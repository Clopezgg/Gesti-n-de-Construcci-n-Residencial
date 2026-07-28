from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.financial.analytics import execute_central_operation, preview_central_operation
from nexora.financial.core import canonical_payload_hash, money
from nexora.financial.db import parse_payload, rollback, savepoint
from nexora.financial.operational_common import MOVEMENT_CATALOG, _document_date, _required
from nexora.financial.operational_income import execute_income, income_preview
from nexora.financial.operational_metadata import record_operation_metadata
from nexora.financial.sources import cancel_fund_source
from nexora.permissions import require_project_access


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
	if movement_code == "102" and not payload.get("economic_category"):
		frappe.throw(_("Seleccione la categoría económica del gasto."))
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
	preview = preview_central_operation(prepared)
	return {
		**preview,
		"movement_code": movement_code,
		"movement_label": MOVEMENT_CATALOG[movement_code]["label"],
		"document_date": prepared["operation_date"],
	}


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
	prepared["preview_hash"] = _required(
		data.get("preview_hash"), "Genere una vista previa antes de ejecutar."
	)
	point = savepoint()
	try:
		result = execute_central_operation(prepared)
		operation = str(result["operation"])
		record_operation_metadata(operation, movement_code)
		return {
			**result,
			"movement_code": movement_code,
			"movement_label": MOVEMENT_CATALOG[movement_code]["label"],
			"document_date": prepared["operation_date"],
		}
	except Exception:
		rollback(point)
		raise
