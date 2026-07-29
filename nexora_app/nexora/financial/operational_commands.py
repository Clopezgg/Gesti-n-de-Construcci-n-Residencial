from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.financial.analytics import execute_central_operation, preview_central_operation
from nexora.financial.core import canonical_payload_hash, money, rate
from nexora.financial.db import parse_payload, rollback, savepoint
from nexora.financial.operational_accounts import (
	_account_row,
	_save_account,
	_validate_account_payload,
	normalize_account_mode,
)
from nexora.financial.operational_common import (
	BANK_CHANNELS,
	MOVEMENT_CATALOG,
	_document_date,
	_normalize_channel,
	_required,
)
from nexora.financial.operational_income import execute_income, income_preview
from nexora.financial.operational_metadata import record_operation_metadata
from nexora.financial.sources import cancel_fund_source
from nexora.permissions import require_project_access


def _expense_account_payload(prepared: Mapping[str, Any]) -> dict[str, Any]:
	return {
		"project": prepared.get("project"),
		"direction": "Destination",
		"account_name": prepared.get("account_name"),
		"origin_or_sender": prepared.get("beneficiary"),
		"institution": prepared.get("institution"),
		"account_reference": prepared.get("account_reference"),
		"currency": prepared.get("currency") or "HNL",
		"default_channel": prepared.get("payment_method") or "Other",
		"notes": prepared.get("account_notes") or "",
	}


def _normalize_expense_currency(prepared: dict[str, Any]) -> None:
	currency = str(prepared.get("currency") or "HNL").strip().upper()
	prepared["currency"] = currency
	if currency == "HNL":
		prepared["exchange_rate"] = 1
		if not prepared.get("amount_hnl") and prepared.get("original_amount"):
			prepared["amount_hnl"] = prepared.get("original_amount")
		prepared["original_amount"] = prepared.get("original_amount") or prepared.get("amount_hnl")
		return
	original = money(prepared.get("original_amount"))
	exchange = rate(prepared.get("exchange_rate"))
	if original <= 0 or exchange <= 0:
		frappe.throw(_("La moneda extranjera requiere importe original y tasa mayores que cero."))
	converted = money(original * exchange)
	if (
		prepared.get("amount_hnl") not in (None, "", 0, "0", "0.00")
		and money(prepared.get("amount_hnl")) != converted
	):
		frappe.throw(_("El importe base no coincide con el importe original multiplicado por la tasa."))
	prepared["original_amount"] = original
	prepared["exchange_rate"] = exchange
	prepared["amount_hnl"] = converted


def _resolve_expense_account(data: Mapping[str, Any]) -> tuple[dict[str, Any], str | None]:
	prepared = dict(data)
	project = _required(prepared.get("project"), "Seleccione un proyecto.")
	require_project_access(project, action="execute")
	account_context_present = any(
		key in prepared
		for key in (
			"account_mode",
			"financial_account",
			"save_financial_account",
			"account_name",
			"institution",
			"account_reference",
		)
	)
	mode = normalize_account_mode(prepared)
	prepared["account_mode"] = mode
	prepared["guided_account_context"] = int(account_context_present)
	prepared["payment_method"] = _normalize_channel(prepared.get("payment_method") or prepared.get("channel"))
	prepared["channel"] = prepared["payment_method"]
	prepared["beneficiary"] = _required(
		prepared.get("beneficiary"), "Seleccione el beneficiario del gasto o pago."
	)
	candidate = str(prepared.get("financial_account") or "").strip()
	account_name: str | None = None

	if mode == "Existing":
		if not candidate:
			frappe.throw(_("Seleccione una cuenta guardada para el beneficiario."))
		account_name = candidate
		account = _account_row(
			candidate,
			project,
			direction="Destination",
			currency=prepared.get("currency"),
			channel=prepared.get("payment_method"),
			counterparty=prepared.get("beneficiary"),
			action="execute",
		)
		prepared.update(
			{
				"beneficiary": account.get("origin_or_sender"),
				"institution": account.get("institution"),
				"account_reference": account.get("account_reference"),
				"currency": account.get("currency") or "HNL",
				"payment_method": account.get("default_channel") or "Other",
				"channel": account.get("default_channel") or "Other",
				"save_financial_account": 0,
			}
		)
	elif mode == "New":
		prepared["financial_account"] = ""
		prepared["save_financial_account"] = 1
	else:
		prepared["financial_account"] = ""
		prepared["save_financial_account"] = 0
		prepared["account_name"] = ""

	_normalize_expense_currency(prepared)
	if prepared["payment_method"] == "Cash":
		prepared["institution"] = ""
		prepared["account_reference"] = ""
	elif prepared["payment_method"] in BANK_CHANNELS and (account_context_present or mode != "Manual"):
		_required(prepared.get("institution"), "El pago requiere banco o institución.")
		_required(prepared.get("account_reference"), "El pago requiere número o referencia de cuenta.")
	if mode == "New":
		_validate_account_payload(_expense_account_payload(prepared), required_direction="Destination")
	return prepared, account_name


def _expense_account_context(prepared: Mapping[str, Any]) -> dict[str, Any]:
	return {
		"account_mode": prepared.get("account_mode"),
		"financial_account": prepared.get("financial_account") or "",
		"account_name": prepared.get("account_name") or "",
		"beneficiary": prepared.get("beneficiary") or "",
		"institution": prepared.get("institution") or "",
		"account_reference": prepared.get("account_reference") or "",
		"currency": prepared.get("currency") or "HNL",
		"original_amount": str(prepared.get("original_amount") or ""),
		"exchange_rate": str(prepared.get("exchange_rate") or ""),
		"amount_hnl": str(prepared.get("amount_hnl") or ""),
		"payment_method": prepared.get("payment_method") or "",
	}


def _central_payload(data: Mapping[str, Any], movement_code: str) -> dict[str, Any]:
	definition = MOVEMENT_CATALOG[movement_code]
	project = _required(data.get("project"), "Seleccione un proyecto.")
	require_project_access(project, action="execute" if movement_code == "102" else "reclassify")
	reference_name = str(data.get("reference_name") or "").strip()
	if movement_code in {"303", "304", "501"} and not reference_name:
		frappe.throw(_("Seleccione el documento original."))
	if reference_name:
		original_project = frappe.db.get_value("NXR Operation", reference_name, "project")
		if not original_project:
			frappe.throw(_("El documento original no existe."))
		if str(original_project) != project:
			frappe.throw(_("La corrección debe conservar el proyecto del documento original."))
	document_date = _document_date(data, reference_name=reference_name)
	description = str(data.get("description") or data.get("reason") or "").strip()
	if movement_code in {"303", "304", "501"} and len(description) < 10:
		frappe.throw(_("Explique el motivo o la corrección con al menos 10 caracteres."))
	payload = {
		**dict(data),
		"operation_code": definition["operation_code"],
		"economic_category": definition["economic_category"] or data.get("economic_category"),
		"project": project,
		"operation_date": document_date,
		"reference_doctype": "NXR Operation" if reference_name else "",
		"reference_name": reference_name,
		"description": description or _("Operación registrada desde la consola operativa NEXORA"),
		"requester": data.get("requester") or frappe.session.user,
		"approved_by": data.get("approved_by") or frappe.session.user,
	}
	if movement_code == "304":
		payload["amount_hnl"] = 0
	elif movement_code in {"303", "501"}:
		payload["amount_hnl"] = data.get("amount_hnl") or 0
	if movement_code == "102":
		if not payload.get("economic_category"):
			frappe.throw(_("Seleccione la categoría económica del gasto."))
		payload, account_name = _resolve_expense_account(payload)
		payload["financial_account"] = account_name or ""
	return payload


def _reference_is_income(reference_name: str) -> bool:
	return frappe.db.get_value("NXR Operation", reference_name, "operation_type") == "Inflow"


def _source_for_income_operation(reference_name: str) -> str:
	source = frappe.db.get_value(
		"NXR Operation Effect",
		{"operation": reference_name, "dimension": "Funds", "effect_type": "Received"},
		"fund_source",
	)
	if not source:
		frappe.throw(_("El ingreso original no conserva una fuente anulable."))
	return str(source)


def _income_cancellation_preview(data: Mapping[str, Any], movement_code: str) -> dict[str, Any]:
	reference_name = _required(data.get("reference_name"), "Seleccione el ingreso original.")
	payload = _central_payload(data, movement_code)
	source_name = _source_for_income_operation(reference_name)
	source = frappe.get_doc("NXR Fund Source", source_name)
	stable = {
		"movement_code": movement_code,
		"reference_name": reference_name,
		"source": source_name,
		"project": source.project,
		"document_date": payload["operation_date"],
		"amount_hnl": f"{money(source.amount_hnl):.2f}",
		"reason": payload["description"],
	}
	return {
		"movement_code": movement_code,
		"movement_label": MOVEMENT_CATALOG[movement_code]["label"],
		"document_date": payload["operation_date"],
		"amount_hnl": stable["amount_hnl"],
		"preview_hash": canonical_payload_hash(stable),
		"document_to_generate": f"Documento compensatorio {movement_code}",
		"reference_name": reference_name,
		"source": source_name,
		"sources": [],
	}


def _central_preview(prepared: Mapping[str, Any], movement_code: str) -> dict[str, Any]:
	preview = preview_central_operation(prepared)
	if movement_code != "102":
		return {
			**preview,
			"movement_code": movement_code,
			"movement_label": MOVEMENT_CATALOG[movement_code]["label"],
			"document_date": prepared["operation_date"],
		}
	financial_preview_hash = str(preview["preview_hash"])
	account_context = _expense_account_context(prepared)
	return {
		**preview,
		"financial_preview_hash": financial_preview_hash,
		"preview_hash": canonical_payload_hash(
			{"financial_preview_hash": financial_preview_hash, "account": account_context}
		),
		"movement_code": movement_code,
		"movement_label": MOVEMENT_CATALOG[movement_code]["label"],
		"document_date": prepared["operation_date"],
		"financial_account": prepared.get("financial_account") or "",
		"account_mode": prepared.get("account_mode") or "Manual",
		"currency": prepared.get("currency") or "HNL",
		"original_amount": f"{money(prepared.get('original_amount')):.2f}",
		"exchange_rate": str(prepared.get("exchange_rate") or 1),
		"counterparty": prepared.get("beneficiary") or "",
		"institution": prepared.get("institution") or "",
		"account_reference": prepared.get("account_reference") or "",
	}


@frappe.whitelist(methods=["POST"])
def preview_operational_movement(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	movement_code = str(data.get("movement_code") or "").strip()
	if movement_code not in MOVEMENT_CATALOG:
		frappe.throw(_("Use un código de movimiento válido: 101, 102, 303, 304 o 501."))
	if movement_code == "101":
		return income_preview(data)
	if movement_code in {"303", "501"} and _reference_is_income(
		_required(data.get("reference_name"), "Seleccione el documento original.")
	):
		return _income_cancellation_preview(data, movement_code)
	prepared = _central_payload(data, movement_code)
	return _central_preview(prepared, movement_code)


def _execute_income_cancellation(data: Mapping[str, Any], movement_code: str) -> dict[str, Any]:
	preview = _income_cancellation_preview(data, movement_code)
	if str(data.get("preview_hash") or "") != preview["preview_hash"]:
		frappe.throw(_("La vista previa de la anulación está vencida. Genérela nuevamente."))
	point = savepoint()
	try:
		result = cancel_fund_source(
			preview["source"],
			str(data.get("description") or data.get("reason") or ""),
			_required(data.get("idempotency_key"), "La operación requiere clave de idempotencia."),
			operation_date=preview["document_date"],
		)
		operation = str(result["reversal_operation"])
		record_operation_metadata(operation, movement_code)
		return {
			**result,
			"operation": operation,
			"movement_code": movement_code,
			"movement_label": MOVEMENT_CATALOG[movement_code]["label"],
			"document_date": preview["document_date"],
		}
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def execute_operational_movement(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	movement_code = str(data.get("movement_code") or "").strip()
	if movement_code not in MOVEMENT_CATALOG:
		frappe.throw(_("Use un código de movimiento válido: 101, 102, 303, 304 o 501."))
	if movement_code == "101":
		return execute_income(data)
	if movement_code in {"303", "501"} and _reference_is_income(
		_required(data.get("reference_name"), "Seleccione el documento original.")
	):
		return _execute_income_cancellation(data, movement_code)
	prepared = _central_payload(data, movement_code)
	prepared["idempotency_key"] = _required(
		data.get("idempotency_key"), "La operación requiere clave de idempotencia."
	)
	provided_preview_hash = _required(data.get("preview_hash"), "Genere una vista previa antes de ejecutar.")
	expected_preview = _central_preview(prepared, movement_code)
	if provided_preview_hash != expected_preview["preview_hash"]:
		frappe.throw(_("La vista previa está vencida o los datos cambiaron. Genérela nuevamente."))
	point = savepoint()
	try:
		account_name = str(prepared.get("financial_account") or "") or None
		reused = False
		if movement_code == "102" and prepared.get("account_mode") == "New":
			account_name, reused = _save_account(
				_expense_account_payload(prepared), required_direction="Destination"
			)
		prepared["financial_account"] = account_name or ""
		prepared["preview_hash"] = expected_preview.get("financial_preview_hash") or provided_preview_hash
		result = execute_central_operation(prepared)
		operation = str(result["operation"])
		record_operation_metadata(operation, movement_code, account_name)
		return {
			**result,
			"movement_code": movement_code,
			"movement_label": MOVEMENT_CATALOG[movement_code]["label"],
			"document_date": prepared["operation_date"],
			"financial_account": account_name,
			"financial_account_reused": reused,
			"account_mode": prepared.get("account_mode") or "Manual",
		}
	except Exception:
		rollback(point)
		raise
