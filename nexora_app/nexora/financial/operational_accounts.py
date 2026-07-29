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

ACCOUNT_DIRECTIONS = {"Origin", "Destination", "Both"}
ACCOUNT_MODES = {"Existing", "New", "Manual"}


def normalize_account_direction(value: object, *, default: str = "Origin") -> str:
	direction = str(value or default).strip() or default
	if direction not in ACCOUNT_DIRECTIONS:
		frappe.throw(_("El uso de la cuenta guardada no es válido."))
	return direction


def normalize_account_mode(data: Mapping[str, Any]) -> str:
	raw = str(data.get("account_mode") or "").strip()
	if not raw:
		if bool(data.get("save_financial_account")):
			return "New"
		if str(data.get("financial_account") or "").strip():
			return "Existing"
		return "Manual"
	normalized = raw[:1].upper() + raw[1:].lower()
	if normalized not in ACCOUNT_MODES:
		frappe.throw(_("La selección de cuenta no es válida."))
	return normalized


def _direction_action(direction: str) -> str:
	return "create_source" if direction == "Origin" else "execute"


def _direction_supports(account_direction: object, requested_direction: str) -> bool:
	value = normalize_account_direction(account_direction)
	return value == "Both" or value == requested_direction


def _normalized_text(value: object) -> str:
	return str(value or "").strip().casefold()


def _account_fingerprint(data: Mapping[str, Any]) -> str:
	return canonical_payload_hash(
		{
			"project": str(data.get("project") or "").strip(),
			"direction": str(data.get("direction") or "Origin").strip(),
			"origin_or_sender": _normalized_text(data.get("origin_or_sender")),
			"institution": _normalized_text(data.get("institution")),
			"account_reference": _normalized_text(data.get("account_reference")),
			"currency": str(data.get("currency") or "HNL").strip().upper(),
			"default_channel": str(data.get("default_channel") or data.get("channel") or "Other").strip(),
		}
	)


def _validate_account_payload(
	data: Mapping[str, Any],
	*,
	required_direction: str | None = None,
) -> dict[str, Any]:
	direction = normalize_account_direction(data.get("direction") or required_direction or "Origin")
	if required_direction and not _direction_supports(
		direction, normalize_account_direction(required_direction)
	):
		frappe.throw(_("La cuenta no es compatible con el sentido de esta operación."))
	action = _direction_action(normalize_account_direction(required_direction or direction))
	project = str(data.get("project") or "").strip()
	if project:
		require_project_access(project, action=action)
	else:
		require_action(action)
	channel = _normalize_channel(data.get("default_channel") or data.get("channel"))
	account = {
		"account_name": _required(data.get("account_name"), "Escriba un nombre para reconocer la cuenta."),
		"active": 1,
		"project": project or None,
		"direction": direction,
		"origin_or_sender": _required(
			data.get("origin_or_sender"), "La cuenta requiere titular, remitente o beneficiario."
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
		frappe.throw(_("La cuenta requiere banco o remesadora y número o referencia de cuenta."))
	account["account_fingerprint"] = _account_fingerprint(account)
	return account


def _account_row(
	name: str,
	project: str | None,
	*,
	direction: str = "Origin",
	currency: object = None,
	channel: object = None,
	counterparty: object = None,
	action: str | None = None,
) -> dict[str, Any]:
	requested_direction = normalize_account_direction(direction)
	project_name = str(project or "").strip()
	permission_action = action or _direction_action(requested_direction)
	if project_name:
		require_project_access(project_name, action=permission_action)
	else:
		require_action(permission_action)
	if not frappe.db.exists("NXR Financial Account", name):
		frappe.throw(
			_("La cuenta guardada no existe. Seleccione una cuenta disponible o use otros datos bancarios.")
		)
	account = frappe.get_doc("NXR Financial Account", name)
	if not frappe.has_permission("NXR Financial Account", ptype="read", doc=account):
		frappe.throw(_("No tiene permiso para utilizar la cuenta seleccionada."), frappe.PermissionError)
	if not account.active:
		frappe.throw(_("La cuenta guardada seleccionada está inactiva."))
	if account.project and str(account.project) != project_name:
		frappe.throw(_("La cuenta guardada no pertenece al proyecto seleccionado."), frappe.PermissionError)
	if not _direction_supports(account.direction, requested_direction):
		frappe.throw(_("La cuenta seleccionada no es compatible con este tipo de movimiento."))
	requested_currency = str(currency or "").strip().upper()
	if requested_currency and str(account.currency or "HNL").strip().upper() != requested_currency:
		frappe.throw(_("La cuenta seleccionada no es compatible con la moneda de la operación."))
	requested_channel = str(channel or "").strip()
	if requested_channel:
		requested_channel = _normalize_channel(requested_channel)
		if str(account.default_channel or "Other") != requested_channel:
			frappe.throw(_("La cuenta seleccionada no es compatible con la forma de recepción o pago."))
	requested_counterparty = _normalized_text(counterparty)
	if requested_counterparty and _normalized_text(account.origin_or_sender) != requested_counterparty:
		frappe.throw(_("La cuenta seleccionada no corresponde a la contraparte de la operación."))
	return account.as_dict()


def _save_account(
	data: Mapping[str, Any],
	*,
	required_direction: str | None = None,
) -> tuple[str, bool]:
	account_data = _validate_account_payload(data, required_direction=required_direction)
	existing = frappe.db.get_value(
		"NXR Financial Account", {"account_fingerprint": account_data["account_fingerprint"]}, "name"
	)
	if existing:
		_account_row(
			str(existing),
			str(account_data.get("project") or "").strip() or None,
			direction=normalize_account_direction(required_direction or account_data.get("direction")),
			currency=account_data.get("currency"),
			channel=account_data.get("default_channel"),
			counterparty=account_data.get("origin_or_sender"),
		)
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
def list_financial_accounts(
	project: str | None = None,
	direction: str = "Origin",
	currency: str | None = None,
	channel: str | None = None,
	counterparty: str | None = None,
) -> list[dict[str, Any]]:
	requested_direction = normalize_account_direction(direction)
	action = _direction_action(requested_direction)
	project_name = str(project or "").strip()
	if project_name:
		require_project_access(project_name, action=action)
	else:
		require_action(action)
	requested_currency = str(currency or "").strip().upper()
	requested_channel = _normalize_channel(channel) if str(channel or "").strip() else ""
	requested_counterparty = _normalized_text(counterparty)
	rows = frappe.get_list(
		"NXR Financial Account",
		filters={"active": 1, "direction": ["in", [requested_direction, "Both"]]},
		fields=[
			"name",
			"account_name",
			"project",
			"direction",
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
	results: list[dict[str, Any]] = []
	for row in rows:
		if row.get("project") and str(row.get("project")) != project_name:
			continue
		if requested_currency and str(row.get("currency") or "HNL").strip().upper() != requested_currency:
			continue
		if requested_channel and str(row.get("default_channel") or "Other") != requested_channel:
			continue
		if requested_counterparty and _normalized_text(row.get("origin_or_sender")) != requested_counterparty:
			continue
		masked = _masked_account(row.get("account_reference"))
		safe_row = dict(row)
		safe_row["account_reference"] = masked
		safe_row["masked_account_reference"] = masked
		safe_row["label"] = " · ".join(
			part
			for part in (
				str(row.get("account_name") or ""),
				str(row.get("institution") or ""),
				masked,
				str(row.get("currency") or ""),
			)
			if part and part != "—"
		)
		results.append(safe_row)
	return results


@frappe.whitelist(methods=["POST"])
def get_financial_account(
	account: str,
	project: str | None = None,
	direction: str = "Origin",
	currency: str | None = None,
	channel: str | None = None,
	counterparty: str | None = None,
) -> dict[str, Any]:
	row = _account_row(
		_required(account, "Seleccione una cuenta guardada."),
		str(project or "").strip() or None,
		direction=direction,
		currency=currency,
		channel=channel,
		counterparty=counterparty,
	)
	masked = _masked_account(row.get("account_reference"))
	row["account_reference"] = masked
	row["masked_account_reference"] = masked
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
			validated = _validate_account_payload(data)
			_account_row(
				str(existing),
				str(validated.get("project") or "").strip() or None,
				direction=validated.get("direction") or "Origin",
				currency=validated.get("currency"),
				channel=validated.get("default_channel"),
				counterparty=validated.get("origin_or_sender"),
			)
			return {"account": str(existing), "reused": True}
		raise
	except Exception:
		rollback(point)
		raise
