from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.financial.core import canonical_payload_hash, money
from nexora.financial.db import rollback, savepoint
from nexora.financial.operational_accounts import _account_row, _save_account
from nexora.financial.operational_common import (
	BANK_CHANNELS,
	CHANNEL_LABELS,
	MOVEMENT_CATALOG,
	_document_date,
	_normalize_channel,
	_required,
)
from nexora.financial.operational_metadata import record_operation_metadata
from nexora.financial.sources import create_fund_source
from nexora.permissions import require_project_access


def resolve_income(data: Mapping[str, Any]) -> tuple[dict[str, Any], str | None]:
	prepared = dict(data)
	project = _required(prepared.get("project"), "Seleccione un proyecto.")
	require_project_access(project, action="create_source")
	account_name = str(prepared.get("financial_account") or "").strip() or None
	if account_name:
		account = _account_row(account_name, project)
		prepared.update(
			{
				"origin_or_sender": account.get("origin_or_sender"),
				"institution": account.get("institution"),
				"account_reference": account.get("account_reference"),
				"currency": account.get("currency") or "HNL",
				"channel": account.get("default_channel") or "Other",
			}
		)
	prepared["channel"] = _normalize_channel(prepared.get("channel"))
	prepared["source_date"] = _document_date(prepared)
	prepared["original_amount"] = money(prepared.get("original_amount", prepared.get("amount_hnl")))
	if prepared["original_amount"] <= 0:
		frappe.throw(_("El importe del ingreso debe ser mayor que cero."))
	prepared["currency"] = str(prepared.get("currency") or "HNL").strip().upper()
	prepared["exchange_rate"] = prepared.get("exchange_rate") or 1
	prepared["origin_or_sender"] = _required(
		prepared.get("origin_or_sender"),
		"El ingreso requiere remitente u origen.",
	)
	if prepared["channel"] in BANK_CHANNELS:
		_required(prepared.get("institution"), "El ingreso requiere banco o remesadora.")
		_required(prepared.get("account_reference"), "El ingreso requiere cuenta destino.")
		_required(prepared.get("external_reference"), "El ingreso requiere número de referencia.")
	prepared["custodian"] = prepared.get("custodian") or frappe.session.user
	prepared["source_name"] = str(prepared.get("source_name") or "").strip() or (
		f"{CHANNEL_LABELS[prepared['channel']]} · {prepared['origin_or_sender']} · {prepared['source_date']}"
	)
	return prepared, account_name


def income_preview(data: Mapping[str, Any]) -> dict[str, Any]:
	prepared, account_name = resolve_income(data)
	stable = {
		key: prepared.get(key)
		for key in (
			"project",
			"source_date",
			"currency",
			"original_amount",
			"exchange_rate",
			"channel",
			"origin_or_sender",
			"institution",
			"account_reference",
			"external_reference",
		)
	}
	stable["movement_code"] = "101"
	stable["financial_account"] = account_name
	return {
		"movement_code": "101",
		"movement_label": MOVEMENT_CATALOG["101"]["label"],
		"document_date": prepared["source_date"],
		"amount_hnl": (f"{money(prepared['original_amount']) * money(prepared['exchange_rate']):.2f}"),
		"preview_hash": canonical_payload_hash(stable),
		"document_to_generate": "Fuente independiente + operación 101",
		"sources": [],
		"account": account_name,
	}


def execute_income(data: Mapping[str, Any]) -> dict[str, Any]:
	preview_hash = str(data.get("preview_hash") or "")
	preview = income_preview(data)
	if not preview_hash or preview_hash != preview["preview_hash"]:
		frappe.throw(_("La vista previa del ingreso está vencida. Genérela nuevamente."))
	prepared, account_name = resolve_income(data)
	point = savepoint()
	try:
		if not account_name and bool(data.get("save_financial_account")):
			account_payload = {
				**prepared,
				"account_name": data.get("account_name"),
				"default_channel": prepared.get("channel"),
				"direction": "Origin",
			}
			account_name, _created = _save_account(account_payload)
		prepared["idempotency_key"] = _required(
			prepared.get("idempotency_key"),
			"La operación requiere clave de idempotencia.",
		)
		result = create_fund_source(prepared)
		record_operation_metadata(str(result["operation"]), "101", account_name)
		return {
			**result,
			"movement_code": "101",
			"movement_label": MOVEMENT_CATALOG["101"]["label"],
			"financial_account": account_name,
			"document_date": prepared["source_date"],
		}
	except Exception:
		rollback(point)
		raise
