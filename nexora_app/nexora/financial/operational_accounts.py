from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.financial.context import service_write
from nexora.financial.core import canonical_payload_hash
from nexora.financial.db import audit, correlation, parse_payload, rollback, savepoint
from nexora.financial.operational_common import (
	BANK_CHANNELS,
	MOVEMENT_CATALOG,
	_masked_account,
	_normalize_channel,
	_required,
)
from nexora.permissions import require_action, require_project_access


def _account_fingerprint(data: Mapping[str, Any]) -> str:
	return canonical_payload_hash(
		{
			"project": str(data.get("project") or "").strip(),
			"direction": str(data.get("direction") or "Origin").strip(),
			"origin_or_sender": str(data.get("origin_or_sender") or "").strip().casefold(),
			"institution": str(data.get("institution") or "").strip().casefold(),
			"account_reference": str(data.get("account_reference") or "").strip().casefold(),
			"currency": str(data.get("currency") or "HNL").strip().upper(),
			"default_channel": str(data.get("default_channel") or data.get("channel") or "Other").strip(),
		}
	)


def _validate_account_payload(data: Mapping[str, Any]) -> dict[str, Any]:
	project = str(data.get("project") or "").strip()
	if project:
		require_project_access(project, action="create_source")
	else:
		require_action("create_source")
	channel = _normalize_channel(data.get("default_channel") or data.get("channel"))
	direction = str(data.get("direction") or "Origin").strip()
	if direction not in {"Origin", "Destination", "Both"}:
		frappe.throw(_("El uso de la cuenta frecuente no es válido."))
	account = {
		"account_name": _required(data.get("account_name"), "Escriba un nombre para la cuenta frecuente."),
		"active": 1,
		"project": project or None,
		"direction": direction,
		"origin_or_sender": _required(
			data.get("origin_or_sender"), "La cuenta frecuente requiere titular o remitente."
		),
		"institution": str(data.get("institution") or "").strip(),
		"account_reference": str(data.get("account_reference") or "").strip(),
		"currency": str(data.get("currency") or "HNL").strip().upper(),
		"default_channel": channel,
		"is_default": int(bool(data.get("is_default"))),
		"notes": str(data.get("notes") or "").strip(),
	}
	if channel == "Cash":
		account["institution"] = ""
		account["account_reference"] = ""
	elif channel in BANK_CHANNELS and (not account["institution"] or not account["account_reference"]):
		frappe.throw(_("La cuenta frecuente requiere banco o remesadora y número de cuenta."))
	account["account_fingerprint"] = _account_fingerprint(account)
	return account


def _account_row(name: str, project: str | None) -> dict[str, Any]:
	if not frappe.db.exists("NXR Financial Account", name):
		frappe.throw(
			_("La cuenta frecuente no existe. Seleccione una cuenta de la lista o use Crear cuenta nueva.")
		)
	account = frappe.get_doc("NXR Financial Account", name)
	if not account.active:
		frappe.throw(_("La cuenta frecuente seleccionada está inactiva."))
	if account.project and str(account.project) != str(project or ""):
		frappe.throw(_("La cuenta frecuente no pertenece al proyecto seleccionado."), frappe.PermissionError)
	if account.direction not in {"Origin", "Both"}:
		frappe.throw(_("La cuenta seleccionada no está habilitada como origen de ingresos."))
	return account.as_dict()


def _save_account(data: Mapping[str, Any]) -> tuple[str, bool]:
	account_data = _validate_account_payload(data)
	existing = frappe.db.get_value(
		"NXR Financial Account", {"account_fingerprint": account_data["account_fingerprint"]}, "name"
	)
	if existing:
		return str(existing), True
	with service_write():
		account = frappe.get_doc({"doctype": "NXR Financial Account", **account_data}).insert(
			ignore_permissions=True
		)
	fingerprint = str(account_data["account_fingerprint"])
	audit(
		"financial_account_created",
		"NXR Financial Account",
		account.name,
		fingerprint,
		correlation(account_data),
		{"account": account.name, "project": account.project, "direction": account.direction},
	)
	return str(account.name), False


@frappe.whitelist(methods=["POST"])
def movement_catalog() -> list[dict[str, str]]:
	require_action("preview")
	return [{"code": code, **definition} for code, definition in MOVEMENT_CATALOG.items()]


@frappe.whitelist(methods=["POST"])
def list_financial_accounts(project: str | None = None) -> list[dict[str, Any]]:
	require_action("create_source")
	project_name = str(project or "").strip()
	if project_name:
		require_project_access(project_name, action="create_source")
	rows = frappe.get_all(
		"NXR Financial Account",
		filters={"active": 1, "direction": ["in", ["Origin", "Both"]]},
		fields=[
			"name",
			"account_name",
			"project",
			"origin_or_sender",
			"institution",
			"account_reference",
			"currency",
			"default_channel",
			"is_default",
		],
		order_by="is_default desc, account_name asc",
		limit_page_length=200,
	)
	return [
		{
			**dict(row),
			"masked_account_reference": _masked_account(row.get("account_reference")),
			"label": " · ".join(
				part
				for part in (
					str(row.get("account_name") or ""),
					str(row.get("institution") or ""),
					_masked_account(row.get("account_reference")),
				)
				if part and part != "—"
			),
		}
		for row in rows
		if not row.get("project") or str(row.get("project")) == project_name
	]


@frappe.whitelist(methods=["POST"])
def get_financial_account(account: str, project: str | None = None) -> dict[str, Any]:
	require_action("create_source")
	project_name = str(project or "").strip()
	if project_name:
		require_project_access(project_name, action="create_source")
	row = _account_row(_required(account, "Seleccione una cuenta frecuente."), project_name or None)
	row["masked_account_reference"] = _masked_account(row.get("account_reference"))
	return row


@frappe.whitelist(methods=["POST"])
def save_financial_account(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	point = savepoint()
	try:
		name, reused = _save_account(data)
		return {"account": name, "reused": reused}
	except frappe.DuplicateEntryError:
		rollback(point)
		fingerprint = _account_fingerprint(data)
		existing = frappe.db.get_value("NXR Financial Account", {"account_fingerprint": fingerprint}, "name")
		if existing:
			return {"account": str(existing), "reused": True}
		raise
	except Exception:
		rollback(point)
		raise
