from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.financial.core import canonical_payload_hash, money
from nexora.financial.db import rollback, savepoint
from nexora.financial.operational_accounts import (
	_account_row,
	_save_account,
	_validate_account_payload,
	normalize_account_mode,
)
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


def _new_account_payload(prepared: Mapping[str, Any]) -> dict[str, Any]:
	return {
		**dict(prepared),
		"account_name": prepared.get("account_name"),
		"default_channel": prepared.get("channel"),
		"direction": "Origin",
	}


def resolve_income(data: Mapping[str, Any]) -> tuple[dict[str, Any], str | None]:
	"""Resolve the source-of-funds record behind movement 101.

	The function name is retained as an internal compatibility boundary; the
	user-facing operation is a fund-source/remittance registration, not an
	"income" transaction.
	"""
	prepared = dict(data)
	project = str(prepared.get("project") or "").strip() or None
	if project:
		require_project_access(project, action="create_source")
	else:
		from nexora.permissions import require_action
		require_action("create_source")
	mode = normalize_account_mode(prepared)
	prepared["account_mode"] = mode
	candidate = str(prepared.get("financial_account") or "").strip()
	account_name: str | None = None

	if mode == "Existing":
		if not candidate:
			frappe.throw(_("Seleccione una cuenta guardada."))
		account_name = candidate
		account = _account_row(
			account_name,
			project,
			direction="Origin",
			currency=prepared.get("currency"),
			channel=prepared.get("channel"),
			counterparty=prepared.get("origin_or_sender"),
		)
		prepared.update(
			{
				"origin_or_sender": account.get("origin_or_sender"),
				"institution": account.get("institution"),
				"account_reference": account.get("account_reference"),
				"currency": account.get("currency") or "HNL",
				"channel": account.get("default_channel") or "Other",
			}
		)
		prepared["save_financial_account"] = 0
	elif mode == "New":
		prepared["financial_account"] = ""
		prepared["save_financial_account"] = 1
	else:
		prepared["financial_account"] = ""
		prepared["save_financial_account"] = 0
		prepared["account_name"] = ""

	prepared["channel"] = _normalize_channel(prepared.get("channel"))
	prepared["source_date"] = _document_date(prepared)
	prepared["original_amount"] = money(prepared.get("original_amount", prepared.get("amount_hnl")))
	if prepared["original_amount"] <= 0:
		frappe.throw(_("El importe de la remesa o fuente debe ser mayor que cero."))
	prepared["currency"] = str(prepared.get("currency") or "HNL").strip().upper()
	prepared["exchange_rate"] = prepared.get("exchange_rate") or 1
	prepared["origin_or_sender"] = _required(
		prepared.get("origin_or_sender"),
		"La remesa o fuente requiere remitente u origen.",
	)
	if prepared["channel"] in BANK_CHANNELS:
		_required(prepared.get("institution"), "La remesa o fuente requiere banco o remesadora.")
		_required(prepared.get("account_reference"), "La remesa o fuente requiere cuenta destino.")
		_required(prepared.get("external_reference"), "La remesa o fuente requiere número de referencia.")
	if mode == "New":
		_validate_account_payload(_new_account_payload(prepared), required_direction="Origin")
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
			"account_mode",
			"account_name",
		)
	}
	stable["movement_code"] = "101"
	stable["financial_account"] = account_name
	return {
		"movement_code": "101",
		"movement_label": MOVEMENT_CATALOG["101"]["label"],
		"document_date": prepared["source_date"],
		"amount_hnl": f"{money(prepared['original_amount']) * money(prepared['exchange_rate']):.2f}",
		"currency": prepared["currency"],
		"original_amount": f"{money(prepared['original_amount']):.2f}",
		"exchange_rate": str(prepared["exchange_rate"]),
		"counterparty": prepared["origin_or_sender"],
		"institution": str(prepared.get("institution") or ""),
		"account_reference": str(prepared.get("account_reference") or ""),
		"preview_hash": canonical_payload_hash(stable),
		"document_to_generate": "Fuente independiente + operación 101",
		"sources": [],
		"account": account_name,
		"account_mode": prepared["account_mode"],
	}


def execute_income(data: Mapping[str, Any]) -> dict[str, Any]:
	preview_hash = str(data.get("preview_hash") or "")
	preview = income_preview(data)
	if not preview_hash or preview_hash != preview["preview_hash"]:
		frappe.throw(_("La vista previa del registro de fondos está vencida. Genérela nuevamente."))
	prepared, account_name = resolve_income(data)
	point = savepoint()
	try:
		reused = False
		if prepared["account_mode"] == "New":
			account_name, reused = _save_account(_new_account_payload(prepared), required_direction="Origin")
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
			"financial_account_reused": reused,
			"account_mode": prepared["account_mode"],
			"document_date": prepared["source_date"],
		}
	except Exception:
		rollback(point)
		raise
