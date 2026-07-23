from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

import frappe
from frappe import _

from nexora.financial.core import FinancialError, money
from nexora.financial.reference_rules import (
	available_amount_from_effects,
	bounded_reference_amount,
	derive_reference_effects,
	validate_return_allocations,
)

REFERENCE_OPERATION_CODES = {
	"ADVANCE_SETTLEMENT",
	"RECLASSIFICATION",
	"REAL_RETURN",
	"REVERSAL_NO_CASH",
	"DOCUMENT_SUBSTITUTION",
}
CORRECTION_OPERATION_CODES = {
	"RECLASSIFICATION",
	"REAL_RETURN",
	"REVERSAL_NO_CASH",
	"DOCUMENT_SUBSTITUTION",
}


def _reference_operation(name: str, *, lock: bool) -> Any:
	if lock:
		row = frappe.db.sql(
			"SELECT name FROM `tabNXR Operation` WHERE name=%s FOR UPDATE",
			name,
		)
		if not row:
			frappe.throw(_("La operación de referencia no existe."))
	if not frappe.db.exists("NXR Operation", name):
		frappe.throw(_("La operación de referencia no existe."))
	operation = frappe.get_doc("NXR Operation", name)
	if operation.status != "Executed":
		frappe.throw(_("La operación de referencia debe estar ejecutada."))
	return operation


def _force_original_project(data: dict[str, Any], original: Any) -> None:
	provided = str(data.get("project") or "").strip()
	if provided and provided != original.project:
		frappe.throw(_("La operación correctiva debe conservar el proyecto del documento original."))
	data["project"] = original.project
	data["reference_doctype"] = "NXR Operation"
	data["reference_name"] = original.name


def _analytic_effects(original_name: str, *, exclude_idempotency_key: str = "") -> list[dict[str, Any]]:
	rows = frappe.db.sql(
		"""
		SELECT
			e.name,
			e.dimension,
			e.amount_hnl,
			e.project,
			e.cost_center,
			e.economic_category,
			e.amount_hnl + COALESCE((
				SELECT SUM(linked.amount_hnl)
				FROM `tabNXR Operation Effect` linked
				INNER JOIN `tabNXR Operation` linked_operation
					ON linked_operation.name = linked.operation
				WHERE linked.reverses_effect = e.name
					AND linked_operation.status = 'Executed'
					AND (%s = '' OR linked_operation.idempotency_key <> %s)
			), 0) AS remaining_hnl
		FROM `tabNXR Operation Effect` e
		WHERE e.operation = %s
			AND e.dimension IN ('Cost', 'Budget', 'Savings', 'Investment')
			AND e.amount_hnl > 0
		ORDER BY e.creation, e.name
		""",
		(exclude_idempotency_key, exclude_idempotency_key, original_name),
		as_dict=True,
	)
	return [dict(row) for row in rows]


def _source_allocations(original_name: str) -> dict[str, Decimal]:
	rows = frappe.db.sql(
		"""
		SELECT fund_source, COALESCE(SUM(allocated_amount_hnl), 0)
		FROM `tabNXR Fund Allocation`
		WHERE operation = %s AND allocation_role = 'Source'
		GROUP BY fund_source
		""",
		original_name,
	)
	return {str(source): money(amount) for source, amount in rows}


def _prior_returns(original_name: str, *, exclude_idempotency_key: str = "") -> dict[str, Decimal]:
	rows = frappe.db.sql(
		"""
		SELECT COALESCE(allocation.related_source, allocation.fund_source),
			COALESCE(SUM(allocation.allocated_amount_hnl), 0)
		FROM `tabNXR Fund Allocation` allocation
		INNER JOIN `tabNXR Operation` operation ON operation.name = allocation.operation
		WHERE operation.reference_doctype = 'NXR Operation'
			AND operation.reference_name = %s
			AND operation.operation_code = 'REAL_RETURN'
			AND operation.status = 'Executed'
			AND (%s = '' OR operation.idempotency_key <> %s)
		GROUP BY COALESCE(allocation.related_source, allocation.fund_source)
		""",
		(original_name, exclude_idempotency_key, exclude_idempotency_key),
	)
	return {str(source): money(amount) for source, amount in rows}


def _consumed_operation_amount(
	original_name: str,
	operation_code: str,
	*,
	exclude_idempotency_key: str = "",
) -> Decimal:
	value = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(amount_hnl), 0)
		FROM `tabNXR Operation`
		WHERE reference_doctype = 'NXR Operation'
			AND reference_name = %s
			AND operation_code = %s
			AND status = 'Executed'
			AND (%s = '' OR idempotency_key <> %s)
		""",
		(original_name, operation_code, exclude_idempotency_key, exclude_idempotency_key),
	)[0][0]
	return money(value)


def _executed_reference_count(
	original_name: str,
	operation_code: str,
	*,
	exclude_idempotency_key: str = "",
) -> int:
	value = frappe.db.sql(
		"""
		SELECT COUNT(*)
		FROM `tabNXR Operation`
		WHERE reference_doctype = 'NXR Operation'
			AND reference_name = %s
			AND operation_code = %s
			AND status = 'Executed'
			AND (%s = '' OR idempotency_key <> %s)
		""",
		(original_name, operation_code, exclude_idempotency_key, exclude_idempotency_key),
	)[0][0]
	return int(value or 0)


def _prepare_effect_correction(
	data: dict[str, Any],
	original: Any,
	*,
	mode: str,
) -> dict[str, Any]:
	key = str(data.get("idempotency_key") or "")
	effects = _analytic_effects(original.name, exclude_idempotency_key=key)
	available = available_amount_from_effects(original.amount_hnl, effects)
	balance = bounded_reference_amount(
		original.amount_hnl,
		money(original.amount_hnl) - available,
		data.get("amount_hnl", data.get("amount")),
		label="analítico",
	)
	data["amount_hnl"] = f"{balance.requested:.2f}"
	data.update(balance.as_payload())
	data["derived_analytic_effects"] = derive_reference_effects(
		original.amount_hnl,
		balance.requested,
		effects,
		mode=mode,
		target_category=data.get("economic_category") if mode == "reclassification" else None,
		target_cost_center=data.get("cost_center") if mode == "reclassification" else None,
	)
	if mode == "reversal":
		data["reversal_of"] = original.name
	return data


def _prepare_real_return(data: dict[str, Any], original: Any) -> dict[str, Any]:
	if original.operation_type not in {"Outflow", "Commitment Execution"}:
		frappe.throw(_("La devolución real debe referenciar una salida ejecutada."))
	if not data.get("evidence"):
		frappe.throw(_("La devolución real requiere evidencia comprobable."))
	original_allocations = _source_allocations(original.name)
	if not original_allocations:
		frappe.throw(_("La salida original no conserva asignaciones recuperables."))
	key = str(data.get("idempotency_key") or "")
	prior = _prior_returns(original.name, exclude_idempotency_key=key)
	try:
		rows, total, total_available = validate_return_allocations(
			original_allocations,
			prior,
			data.get("allocations") or [],
		)
	except FinancialError as exc:
		frappe.throw(_(str(exc)))
	requested = money(data.get("amount_hnl", data.get("amount")))
	if requested and requested != total:
		frappe.throw(_("El importe de la devolución debe coincidir con sus asignaciones."))
	for row in rows:
		target_project = frappe.db.get_value("NXR Fund Source", row["source"], "project")
		if target_project != original.project:
			frappe.throw(_("La fuente de restitución debe pertenecer al proyecto de la salida original."))
	data["allocations"] = rows
	data["amount_hnl"] = f"{total:.2f}"
	data["reference_amount_hnl"] = f"{money(sum(original_allocations.values())):.2f}"
	data["reference_balance_before_hnl"] = f"{total_available:.2f}"
	data["reference_balance_after_hnl"] = f"{money(total_available - total):.2f}"
	return data


def _prepare_advance_settlement(data: dict[str, Any], original: Any) -> dict[str, Any]:
	if original.operation_code != "ADVANCE_DISBURSEMENT" or original.operation_type != "Outflow":
		frappe.throw(_("La liquidación debe referenciar un desembolso de anticipo ejecutado."))
	beneficiary = str(data.get("beneficiary") or original.beneficiary or "").strip()
	if not beneficiary:
		frappe.throw(_("El anticipo original no conserva beneficiario o responsable."))
	if data.get("beneficiary") and str(data["beneficiary"]) != str(original.beneficiary):
		frappe.throw(_("La liquidación debe conservar el beneficiario o responsable del anticipo."))
	key = str(data.get("idempotency_key") or "")
	settled = _consumed_operation_amount(
		original.name,
		"ADVANCE_SETTLEMENT",
		exclude_idempotency_key=key,
	)
	try:
		balance = bounded_reference_amount(
			original.amount_hnl,
			settled,
			data.get("amount_hnl", data.get("amount")),
			label="de liquidación",
		)
	except FinancialError as exc:
		frappe.throw(_(str(exc)))
	data["amount_hnl"] = f"{balance.requested:.2f}"
	data["beneficiary_doctype"] = original.beneficiary_doctype
	data["beneficiary"] = beneficiary
	data["due_date"] = original.due_date
	data["allocations"] = []
	data.update(balance.as_payload())
	return data


def _prepare_document_substitution(data: dict[str, Any], original: Any) -> dict[str, Any]:
	key = str(data.get("idempotency_key") or "")
	prior = _executed_reference_count(
		original.name,
		"DOCUMENT_SUBSTITUTION",
		exclude_idempotency_key=key,
	)
	if prior:
		frappe.throw(_("El documento original ya tiene una sustitución documental ejecutada."))
	data["amount_hnl"] = "0.00"
	data["substitutes_operation"] = original.name
	data["reference_amount_hnl"] = f"{money(original.amount_hnl):.2f}"
	data["reference_balance_before_hnl"] = "0.00"
	data["reference_balance_after_hnl"] = "0.00"
	data["allocations"] = []
	return data


def prepare_reference_operation(data: Mapping[str, Any], *, lock: bool) -> dict[str, Any]:
	prepared = dict(data)
	code = str(prepared.get("operation_code") or "")
	if code not in REFERENCE_OPERATION_CODES:
		return prepared
	original = _reference_operation(str(prepared.get("reference_name") or ""), lock=lock)
	_force_original_project(prepared, original)
	if code in CORRECTION_OPERATION_CODES and original.operation_code in CORRECTION_OPERATION_CODES:
		frappe.throw(_("La corrección debe referenciar una operación base, no otra corrección."))
	try:
		if code == "RECLASSIFICATION":
			return _prepare_effect_correction(prepared, original, mode="reclassification")
		if code == "REVERSAL_NO_CASH":
			return _prepare_effect_correction(prepared, original, mode="reversal")
		if code == "REAL_RETURN":
			return _prepare_real_return(prepared, original)
		if code == "ADVANCE_SETTLEMENT":
			return _prepare_advance_settlement(prepared, original)
		if code == "DOCUMENT_SUBSTITUTION":
			return _prepare_document_substitution(prepared, original)
	except FinancialError as exc:
		frappe.throw(_(str(exc)))
	return prepared


def advance_status(name: str) -> dict[str, Any]:
	operation = _reference_operation(name, lock=False)
	if operation.operation_code != "ADVANCE_DISBURSEMENT":
		frappe.throw(_("El documento indicado no es un desembolso de anticipo."))
	settled = _consumed_operation_amount(operation.name, "ADVANCE_SETTLEMENT")
	total = money(operation.amount_hnl)
	if settled > total:
		frappe.throw(_("Las liquidaciones del anticipo superan el total entregado."))
	return {
		"operation": operation.name,
		"document_number": operation.document_number,
		"beneficiary_doctype": operation.beneficiary_doctype,
		"beneficiary": operation.beneficiary,
		"operation_date": operation.operation_date,
		"due_date": operation.due_date,
		"total_disbursed_hnl": f"{total:.2f}",
		"total_settled_hnl": f"{settled:.2f}",
		"outstanding_hnl": f"{money(total - settled):.2f}",
	}
