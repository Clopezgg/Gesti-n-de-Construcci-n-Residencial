from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.financial.context import service_write
from nexora.financial.core import canonical_payload_hash, money
from nexora.financial.db import (
	audit,
	complete_idempotency,
	correlation,
	issue_document_number,
	link_sequence,
	operation_doc,
	parse_payload,
	rollback,
	savepoint,
	source_states,
	start_idempotency,
)
from nexora.permissions import require_action


@frappe.whitelist(methods=["POST"])
def list_source_balances(project: str) -> list[dict[str, str]]:
	require_action("read_balances")
	names = frappe.get_all(
		"NXR Fund Source",
		filters={"project": project, "status": ["in", ["Active", "Exhausted"]]},
		pluck="name",
		order_by="name asc",
	)
	states = source_states(names)
	return [
		{
			"source": name,
			"balance_hnl": f"{states[name].funds:.2f}",
			"reserved_hnl": f"{states[name].reserved:.2f}",
			"available_hnl": f"{states[name].available:.2f}",
		}
		for name in names
	]


@frappe.whitelist(methods=["POST"])
def create_fund_source(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("create_source")
	data = parse_payload(payload)
	data["idempotency_key"] = str(data.get("idempotency_key") or "")
	source_date = frappe.utils.getdate(data.get("source_date") or frappe.utils.today())
	data["source_date"] = source_date.isoformat()
	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(data["idempotency_key"], fingerprint, correlation_id)
		if cached is not None:
			return cached
		source_number, source_sequence = issue_document_number("NXR Fund Source", data["idempotency_key"])
		with service_write():
			source = frappe.get_doc(
				{
					"doctype": "NXR Fund Source",
					"source_code": source_number,
					"source_name": data.get("source_name") or f"Fuente {source_number}",
					"channel": data["channel"],
					"project": data["project"],
					"source_date": data["source_date"],
					"currency": data.get("currency") or "HNL",
					"original_amount": data["original_amount"],
					"exchange_rate": data.get("exchange_rate") or 1,
					"origin_or_sender": data["origin_or_sender"],
					"custodian": data.get("custodian") or frappe.session.user,
					"institution": data.get("institution"),
					"account_reference": data.get("account_reference"),
					"external_reference": data.get("external_reference"),
					"evidence": data.get("evidence"),
					"status": "Active",
				}
			).insert(ignore_permissions=True)
		link_sequence(source_sequence, source.name)
		operation_number, operation_sequence = issue_document_number("NXR Operation", data["idempotency_key"])
		operation_payload = {
			**data,
			"operation_type": "Inflow",
			"operation_date": source.source_date,
			"amount_hnl": source.amount_hnl,
			"amount": source.amount_hnl,
			"project": source.project,
		}
		preview_data = {
			"preview_hash": canonical_payload_hash(
				{"source": source.name, "amount_hnl": str(source.amount_hnl)}
			),
			"sources": [],
		}
		operation = operation_doc(
			operation_payload, operation_number, fingerprint, preview_data, correlation_id
		)
		link_sequence(operation_sequence, operation.name)
		with service_write():
			frappe.get_doc(
				{
					"doctype": "NXR Operation Effect",
					"operation": operation.name,
					"fund_source": source.name,
					"dimension": "Funds",
					"effect_type": "Received",
					"amount_hnl": source.amount_hnl,
					"project": source.project,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
		result = {
			"fund_source": source.name,
			"source_number": source_number,
			"operation": operation.name,
			"document_number": operation_number,
			"amount_hnl": f"{money(source.amount_hnl):.2f}",
		}
		audit("fund_source_created", "NXR Fund Source", source.name, fingerprint, correlation_id, result)
		complete_idempotency(idem, "NXR Fund Source", source.name, result)
		return result
	except Exception:
		rollback(point)
		raise


def _validate_cancellable_source(source_doc: Any) -> tuple[Any, Any]:
	if source_doc.status == "Cancelled":
		frappe.throw(_("Este ingreso ya está anulado."))
	if source_doc.status not in {"Active", "Exhausted"}:
		frappe.throw(_("Solo se pueden anular ingresos activos o agotados."))

	effects = frappe.get_all(
		"NXR Operation Effect",
		filters={"fund_source": source_doc.name},
		fields=["name", "operation", "dimension", "effect_type", "amount_hnl"],
		order_by="creation asc, name asc",
	)
	if len(effects) != 1:
		frappe.throw(
			_(
				"Este ingreso ya tiene movimientos relacionados. Revierta primero los gastos, reservas o ajustes vinculados."
			)
		)
	initial_effect = effects[0]
	if (
		initial_effect.dimension != "Funds"
		or initial_effect.effect_type != "Received"
		or money(initial_effect.amount_hnl) != money(source_doc.amount_hnl)
	):
		frappe.throw(_("El ingreso no conserva su efecto inicial íntegro y no puede anularse directamente."))

	state = source_states([source_doc.name], current_read=True)[source_doc.name]
	if state.reserved != 0 or state.funds != money(source_doc.amount_hnl):
		frappe.throw(
			_("El ingreso tiene saldo comprometido o movimientos aplicados y requiere una reversión previa.")
		)

	original_operation = frappe.get_doc("NXR Operation", initial_effect.operation)
	if original_operation.operation_type != "Inflow":
		frappe.throw(_("No se encontró la operación original de ingreso."))
	return initial_effect, original_operation


def _cancel_fund_source(
	source_doc: Any,
	reason: str,
	idempotency_key: str,
	*,
	persist_source: bool,
	operation_date: str | None = None,
) -> dict[str, Any]:
	require_action("cancel_source")
	cancellation_reason = str(reason or "").strip()
	key = str(idempotency_key or "").strip()
	if len(cancellation_reason) < 10:
		frappe.throw(_("Explique el motivo de la anulación con al menos 10 caracteres."))

	locked = frappe.db.sql(
		"SELECT name FROM `tabNXR Fund Source` WHERE name=%s FOR UPDATE",
		source_doc.name,
	)
	if not locked:
		frappe.throw(_("El ingreso indicado no existe."))
	initial_effect, original_operation = _validate_cancellable_source(source_doc)

	payload = {
		"source": source_doc.name,
		"reason": cancellation_reason,
		"idempotency_key": key,
		"operation_type": "Analytic Adjustment",
		"operation_date": operation_date or frappe.utils.today(),
		"project": source_doc.project,
		"amount_hnl": source_doc.amount_hnl,
		"amount": source_doc.amount_hnl,
		"reference_doctype": "NXR Fund Source",
		"reference_name": source_doc.name,
		"reversal_of": original_operation.name,
		"requester": frappe.session.user,
		"approved_by": frappe.session.user,
	}
	fingerprint = canonical_payload_hash(payload)
	correlation_id = correlation(payload)
	idem, cached = start_idempotency(key, fingerprint, correlation_id)
	if cached is not None:
		return cached

	operation_number, sequence_name = issue_document_number("NXR Operation", key)
	preview_data = {
		"preview_hash": canonical_payload_hash(
			{
				"source": source_doc.name,
				"amount_hnl": str(source_doc.amount_hnl),
				"reason": cancellation_reason,
			}
		),
		"sources": [],
	}
	reversal = operation_doc(payload, operation_number, fingerprint, preview_data, correlation_id)
	link_sequence(sequence_name, reversal.name)

	with service_write():
		frappe.get_doc(
			{
				"doctype": "NXR Operation Effect",
				"operation": reversal.name,
				"fund_source": source_doc.name,
				"dimension": "Funds",
				"effect_type": "Reversed",
				"amount_hnl": -money(source_doc.amount_hnl),
				"project": source_doc.project,
				"is_reversal": 1,
				"reverses_effect": initial_effect.name,
				"correlation_id": correlation_id,
			}
		).insert(ignore_permissions=True)
		original_operation.status = "Compensated Total"
		original_operation.save(ignore_permissions=True)

	source_doc.status = "Cancelled"
	source_doc.cancellation_reason = cancellation_reason
	source_doc.cancellation_operation = reversal.name
	source_doc.cancelled_by = frappe.session.user
	source_doc.cancelled_at = frappe.utils.now_datetime()
	source_doc.request_cancellation = 0
	if persist_source:
		with service_write():
			source_doc.save(ignore_permissions=True)

	result = {
		"fund_source": source_doc.name,
		"status": "Cancelled",
		"reversal_operation": reversal.name,
		"document_number": operation_number,
		"amount_hnl": f"{money(source_doc.amount_hnl):.2f}",
		"reason": cancellation_reason,
	}
	audit("fund_source_cancelled", "NXR Fund Source", source_doc.name, fingerprint, correlation_id, result)
	complete_idempotency(idem, "NXR Fund Source", source_doc.name, result)
	return result


def cancel_fund_source_document(source_doc: Any, reason: str) -> dict[str, Any]:
	"""Apply a safe cancellation requested from the standard Frappe form."""
	return _cancel_fund_source(
		source_doc,
		reason,
		f"cancel-source-{source_doc.name}",
		persist_source=False,
		operation_date=frappe.utils.today(),
	)


@frappe.whitelist(methods=["POST"])
def cancel_fund_source(
	source: str,
	reason: str,
	idempotency_key: str,
	operation_date: str | None = None,
) -> dict[str, Any]:
	"""Compensate an unused incorrect income without deleting its audit trail."""
	source_name = str(source or "").strip()
	if not source_name:
		frappe.throw(_("Seleccione el ingreso que desea anular."))
	point = savepoint()
	try:
		source_doc = frappe.get_doc("NXR Fund Source", source_name)
		return _cancel_fund_source(
			source_doc,
			reason,
			idempotency_key,
			persist_source=True,
			operation_date=operation_date or frappe.utils.today(),
		)
	except Exception:
		rollback(point)
		raise
