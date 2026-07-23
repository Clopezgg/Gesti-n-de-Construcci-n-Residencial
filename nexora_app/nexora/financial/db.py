from __future__ import annotations

import json
import uuid
from decimal import Decimal
from typing import Any, Mapping, Sequence

import frappe
from frappe import _

from nexora.financial.context import service_write
from nexora.financial.core import FinancialError, SourceState, preview_operation


def parse_payload(value: str | Mapping[str, Any]) -> dict[str, Any]:
	parsed = json.loads(value) if isinstance(value, str) else dict(value)
	if not isinstance(parsed, dict):
		frappe.throw(_("El payload debe ser un objeto JSON."))
	return parsed


def savepoint() -> str:
	name = f"nexora_{uuid.uuid4().hex}"
	frappe.db.savepoint(name)
	return name


def rollback(name: str) -> None:
	frappe.db.rollback(save_point=name)


def correlation(payload: Mapping[str, Any]) -> str:
	return str(payload.get("correlation_id") or uuid.uuid4().hex)


def start_idempotency(key: str, fingerprint: str, correlation_id: str) -> tuple[Any, dict[str, Any] | None]:
	if not key or len(key) > 140:
		frappe.throw(_("La clave de idempotencia es obligatoria y no puede superar 140 caracteres."))
	try:
		with service_write():
			record = frappe.get_doc(
				{
					"doctype": "NXR Idempotency Record",
					"idempotency_key": key,
					"payload_hash": fingerprint,
					"status": "Processing",
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
		return record, None
	except frappe.DuplicateEntryError:
		record = frappe.get_doc("NXR Idempotency Record", key)
		if record.payload_hash != fingerprint:
			frappe.throw(_("La clave de idempotencia ya fue usada con un payload diferente."))
		if record.status == "Completed" and record.response_json:
			return record, json.loads(record.response_json)
		frappe.throw(_("La misma solicitud ya está en procesamiento."))


def complete_idempotency(record: Any, doctype: str, name: str, response: Mapping[str, Any]) -> None:
	record.status = "Completed"
	record.result_doctype = doctype
	record.result_name = name
	record.response_json = json.dumps(response, ensure_ascii=False, sort_keys=True, default=str)
	with service_write():
		record.save(ignore_permissions=True)


def issue_document_number(doctype: str, idempotency_key: str) -> tuple[str, str]:
	frappe.db.sql("INSERT INTO `tabNXR Document Sequence Counter` (`issued_at`) VALUES (NOW(6))")
	value = int(frappe.db.sql("SELECT LAST_INSERT_ID()")[0][0])
	if value > 999_999_999_999:
		frappe.throw(_("La secuencia global de 12 dígitos se agotó."))
	number = f"{value:012d}"
	with service_write():
		sequence = frappe.get_doc(
			{
				"doctype": "NXR Document Sequence",
				"number": number,
				"issued_for_doctype": doctype,
				"idempotency_key": idempotency_key,
				"status": "Reserved",
			}
		).insert(ignore_permissions=True)
	return number, sequence.name


def link_sequence(sequence_name: str, document_name: str) -> None:
	sequence = frappe.get_doc("NXR Document Sequence", sequence_name)
	sequence.issued_for_name = document_name
	sequence.status = "Linked"
	with service_write():
		sequence.save(ignore_permissions=True)


def audit(event: str, doctype: str, name: str, fingerprint: str, correlation_id: str, after: Any) -> None:
	with service_write():
		frappe.get_doc(
			{
				"doctype": "NXR Audit Event",
				"event_type": event,
				"actor": frappe.session.user,
				"reference_doctype": doctype,
				"reference_name": name,
				"payload_hash": fingerprint,
				"after_json": json.dumps(after, ensure_ascii=False, sort_keys=True, default=str),
				"correlation_id": correlation_id,
			}
		).insert(ignore_permissions=True)


def lock_sources(source_names: Sequence[str]) -> tuple[str, ...]:
	ordered = tuple(sorted(set(source_names)))
	if not ordered:
		return ordered
	source = frappe.qb.DocType("NXR Fund Source")
	rows = (
		frappe.qb.from_(source)
		.select(source.name)
		.where(source.name.isin(ordered))
		.orderby(source.name)
		.for_update()
	).run()
	found = tuple(row[0] for row in rows)
	if found != ordered:
		missing = sorted(set(ordered) - set(found))
		frappe.throw(_("Fuentes inexistentes o no disponibles: {0}").format(", ".join(missing)))
	return ordered


def source_states(source_names: Sequence[str], *, current_read: bool = False) -> dict[str, SourceState]:
	states: dict[str, SourceState] = {}
	for source in source_names:
		if current_read:
			rows = frappe.db.sql(
				"""SELECT dimension, amount_hnl
				   FROM `tabNXR Operation Effect`
				   WHERE fund_source=%s
				   ORDER BY creation, name FOR UPDATE""",
				source,
			)
			funds = sum((Decimal(row[1]) for row in rows if row[0] == "Funds"), Decimal("0"))
			reserved = sum((Decimal(row[1]) for row in rows if row[0] == "Reserved"), Decimal("0"))
			states[source] = SourceState.from_values(funds, reserved)
			continue
		row = frappe.db.sql(
			"""SELECT
				COALESCE(SUM(CASE WHEN dimension='Funds' THEN amount_hnl ELSE 0 END),0),
				COALESCE(SUM(CASE WHEN dimension='Reserved' THEN amount_hnl ELSE 0 END),0)
			   FROM `tabNXR Operation Effect` WHERE fund_source=%s""",
			source,
		)[0]
		states[source] = SourceState.from_values(row[0], row[1])
	return states


def preview(payload: Mapping[str, Any], *, lock: bool) -> dict[str, Any]:
	allocations = payload.get("allocations") or []
	names = [str(row.get("source") or row.get("fund_source") or "") for row in allocations]
	if payload.get("destination_source"):
		names.append(str(payload["destination_source"]))
	ordered = lock_sources(names) if lock else tuple(sorted(set(names)))
	try:
		return preview_operation(payload, source_states(ordered, current_read=lock))
	except FinancialError as exc:
		frappe.throw(_(str(exc)))


def operation_doc(
	payload: Mapping[str, Any],
	number: str,
	fingerprint: str,
	preview_data: Mapping[str, Any],
	correlation_id: str,
	commitment: str | None = None,
) -> Any:
	with service_write():
		return frappe.get_doc(
			{
				"doctype": "NXR Operation",
				"document_number": number,
				"operation_code": payload.get("operation_code"),
				"operation_type": payload["operation_type"],
				"status": "Executed",
				"project": payload["project"],
				"target_project": payload.get("target_project"),
				"destination_source": payload.get("destination_source"),
				"operation_date": payload.get("operation_date") or frappe.utils.today(),
				"due_date": payload.get("due_date"),
				"currency": "HNL",
				"amount": payload.get("amount_hnl", payload.get("amount", 0)),
				"exchange_rate": 1,
				"beneficiary_doctype": payload.get("beneficiary_doctype"),
				"beneficiary": payload.get("beneficiary"),
				"cost_center": payload.get("cost_center"),
				"economic_category": payload.get("economic_category"),
				"payment_method": payload.get("payment_method"),
				"external_reference": payload.get("external_reference"),
				"affects_cost": int(bool(payload.get("affects_cost"))),
				"affects_budget": int(bool(payload.get("affects_budget"))),
				"commitment": commitment,
				"idempotency_key": payload["idempotency_key"],
				"payload_hash": fingerprint,
				"preview_hash": preview_data["preview_hash"],
				"requester": payload.get("requester"),
				"approved_by": payload.get("approved_by"),
				"executed_by": frappe.session.user,
				"evidence": payload.get("evidence"),
				"reference_doctype": payload.get("reference_doctype"),
				"reference_name": payload.get("reference_name"),
				"reference_amount_hnl": preview_data.get("reference_amount_hnl") or 0,
				"reference_balance_before_hnl": (
					preview_data.get("reference_balance_before_hnl") or 0
				),
				"reference_balance_after_hnl": (
					preview_data.get("reference_balance_after_hnl") or 0
				),
				"reversal_of": payload.get("reversal_of"),
				"substitutes_operation": payload.get("substitutes_operation"),
				"correlation_id": correlation_id,
			}
		).insert(ignore_permissions=True)


def persist_effects(
	operation: Any, preview_data: Mapping[str, Any], correlation_id: str, commitment: str | None = None
) -> None:
	effect_type = {
		"Outflow": "Executed",
		"Commitment Reserve": "Reserved",
		"Commitment Execution": "Executed",
		"Commitment Release": "Released",
		"Internal Transfer": "Internal Transfer",
		"Real Return": "Real Return",
		"Analytic Adjustment": "Analytic Adjustment",
		"Reclassification": "Reclassification",
	}.get(operation.operation_type, "Analytic Adjustment")
	with service_write():
		for order, row in enumerate(preview_data["sources"], start=1):
			frappe.get_doc(
				{
					"doctype": "NXR Fund Allocation",
					"operation": operation.name,
					"fund_source": row["source"],
					"related_source": row.get("related_source"),
					"commitment": commitment,
					"allocation_role": row.get("allocation_role") or "Source",
					"allocated_amount_hnl": row["amount_hnl"],
					"balance_before_hnl": row["balance_before_hnl"],
					"balance_after_hnl": row["balance_after_hnl"],
					"reserved_before_hnl": row["reserved_before_hnl"],
					"reserved_after_hnl": row["reserved_after_hnl"],
					"allocation_order": order,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
			if (
				getattr(frappe.flags, "in_test", False)
				and getattr(frappe.flags, "nexora_fail_after_allocation", None) == order
			):
				frappe.throw(
					_("Fallo de integración NEXORA inyectado después de la asignación {0}.").format(order)
				)
			for dimension, delta in (
				("Funds", Decimal(row["funds_delta_hnl"])),
				("Reserved", Decimal(row["reserved_delta_hnl"])),
			):
				if delta:
					frappe.get_doc(
						{
							"doctype": "NXR Operation Effect",
							"operation": operation.name,
							"fund_source": row["source"],
							"commitment": commitment,
							"dimension": dimension,
							"effect_type": effect_type,
							"amount_hnl": delta,
							"project": row.get("project") or operation.project,
							"cost_center": operation.cost_center,
							"economic_category": operation.economic_category,
							"correlation_id": correlation_id,
						}
					).insert(ignore_permissions=True)
		for row in preview_data["sources"]:
			status = "Exhausted" if Decimal(row["balance_after_hnl"]) == 0 else "Active"
			frappe.db.set_value("NXR Fund Source", row["source"], "status", status, update_modified=False)
		for analytic in preview_data.get("analytic_effects") or []:
			dimension = analytic["dimension"]
			default_effect = {
				"Cost": "Cost Recognized",
				"Budget": (
					"Budget Reserved"
					if operation.operation_type == "Commitment Reserve"
					else "Budget Executed"
				),
				"Savings": "Savings Applied",
				"Investment": "Investment Applied",
			}[dimension]
			frappe.get_doc(
				{
					"doctype": "NXR Operation Effect",
					"operation": operation.name,
					"commitment": commitment,
					"dimension": dimension,
					"effect_type": analytic.get("effect_type") or default_effect,
					"amount_hnl": analytic["amount_hnl"],
					"project": analytic.get("project") or operation.project,
					"cost_center": analytic.get("cost_center"),
					"economic_category": (
						analytic.get("economic_category") or operation.economic_category
					),
					"is_reversal": int(bool(analytic.get("is_reversal"))),
					"reverses_effect": analytic.get("reverses_effect"),
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)


def commitment_outstanding(name: str) -> Decimal:
	value = frappe.db.sql(
		"SELECT COALESCE(SUM(amount_hnl),0) FROM `tabNXR Operation Effect` WHERE commitment=%s AND dimension='Reserved'",
		name,
	)[0][0]
	from nexora.financial.core import money

	return money(value)
