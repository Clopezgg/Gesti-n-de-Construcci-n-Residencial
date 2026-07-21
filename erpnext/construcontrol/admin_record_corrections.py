from __future__ import annotations

import secrets
from typing import Any

import frappe
from frappe import _
from frappe.utils import flt, now_datetime

from erpnext.construcontrol.admin_corrections import (
	_correction_context,
	_evidence,
	_fingerprint,
	_parse_mapping,
	_reason,
	_require_token,
)
from erpnext.construcontrol.audit import record_manual_event

_SCHEMAS: dict[str, dict[str, Any]] = {
	"CC Funding Source": {
		"module": "FI01",
		"fields": {
			"project",
			"title",
			"income_type",
			"status",
			"date_sent",
			"date_received",
			"currency",
			"original_amount",
			"exchange_rate",
			"gross_amount",
			"fee_amount",
			"original_currency",
			"treasury_exchange_rate",
			"net_amount_hnl",
			"transaction_channel",
			"financial_institution",
			"transaction_reference",
			"reconciliation_status",
			"sender",
			"origin_country",
			"remittance_company",
			"bank",
			"reference",
			"notes",
		},
		"financial": {
			"status",
			"original_amount",
			"exchange_rate",
			"gross_amount",
			"fee_amount",
			"net_amount_hnl",
			"treasury_exchange_rate",
			"reconciliation_status",
		},
		"derived": {"amount_hnl", "spent_hnl", "pending_hnl", "available_hnl", "projected_hnl"},
	},
	"CC Construction Phase": {
		"module": "PR01",
		"fields": {
			"project",
			"task",
			"phase_order",
			"phase_name",
			"status",
			"risk",
			"budget_hnl",
			"progress_percent",
			"responsible",
			"responsible_user",
			"target_start_date",
			"target_end_date",
			"description",
			"milestone_date",
			"dependencies",
		},
		"financial": {"budget_hnl"},
		"derived": {
			"committed_hnl",
			"actual_cost_hnl",
			"available_budget_hnl",
			"financial_progress_percent",
			"schedule_status",
		},
	},
	"CC Labor Contract": {
		"module": "CO01",
		"fields": {
			"project",
			"phase",
			"contract",
			"contract_code",
			"contractor_name",
			"supplier",
			"status",
			"start_date",
			"target_end_date",
			"project_scope",
			"contract_mode",
			"project_value_hnl",
			"labor_value_hnl",
			"materials_included",
			"materials_not_included",
			"notes",
		},
		"financial": {"status", "project_value_hnl", "labor_value_hnl", "supplier"},
		"derived": {"paid_hnl", "balance_hnl"},
	},
}


def _schema(doctype: str) -> dict[str, Any]:
	doctype = str(doctype or "").strip()
	if doctype not in _SCHEMAS:
		frappe.throw(_("Ese tipo de registro no admite corrección administrativa."))
	if not frappe.db.exists("DocType", doctype):
		frappe.throw(_("El tipo de registro seleccionado no existe en este sitio."))
	return _SCHEMAS[doctype]


def _snapshot(doc: Any, schema: dict[str, Any]) -> dict[str, Any]:
	fields = set(schema["fields"]) | set(schema["derived"]) | {
		"name",
		"source_id",
		"source_key",
		"is_logically_deleted",
	}
	return {field: doc.get(field) for field in sorted(fields) if doc.meta.has_field(field)}


def _prepare(
	doctype: str,
	name: str,
	changes: Any,
	reason: str,
	evidence: str,
) -> dict[str, Any]:
	schema = _schema(doctype)
	name = str(name or "").strip()
	if not name or not frappe.db.exists(doctype, name):
		frappe.throw(_("El registro seleccionado no existe."))
	doc = frappe.get_doc(doctype, name)
	before = _snapshot(doc, schema)
	requested = _parse_mapping(changes)
	unknown = sorted(set(requested) - set(schema["fields"]))
	if unknown:
		frappe.throw(_("Campos no autorizados: {0}").format(", ".join(unknown)))
	if not requested:
		frappe.throw(_("Indique al menos un cambio."))
	for field, value in requested.items():
		if doc.meta.has_field(field):
			doc.set(field, value)
	with _correction_context():
		doc.run_method("validate")
	proposed = _snapshot(doc, schema)
	reason = _reason(reason)
	evidence = _evidence(evidence, bool(set(requested) & set(schema["financial"])))
	impact = {
		"changed_fields": sorted(
			field for field in proposed if field != "name" and before.get(field) != proposed.get(field)
		),
		"project_before": before.get("project"),
		"project_after": proposed.get("project"),
	}
	if doctype == "CC Funding Source":
		impact.update(
			{
				"received_before": flt(before.get("amount_hnl") or before.get("net_amount_hnl")),
				"received_after": flt(proposed.get("amount_hnl") or proposed.get("net_amount_hnl")),
				"available_before": flt(before.get("available_hnl")),
				"available_after": flt(proposed.get("available_hnl")),
			}
		)
	elif doctype == "CC Labor Contract":
		impact.update(
			{
				"value_before": flt(before.get("project_value_hnl") or before.get("labor_value_hnl")),
				"value_after": flt(proposed.get("project_value_hnl") or proposed.get("labor_value_hnl")),
				"paid_hnl": flt(proposed.get("paid_hnl")),
				"balance_hnl": flt(proposed.get("balance_hnl")),
			}
		)
	elif doctype == "CC Construction Phase":
		impact.update(
			{
				"budget_before": flt(before.get("budget_hnl")),
				"budget_after": flt(proposed.get("budget_hnl")),
				"actual_cost_hnl": flt(proposed.get("actual_cost_hnl")),
			}
		)
	payload = {
		"doctype": doctype,
		"name": name,
		"module": schema["module"],
		"reason": reason,
		"evidence": evidence,
		"changes": requested,
		"before": before,
		"proposed": proposed,
		"impact": impact,
	}
	payload["preview_hash"] = _fingerprint(payload)
	return payload


def _recalculate(doctype: str, before: dict[str, Any], after: dict[str, Any]) -> None:
	from erpnext.construcontrol.construction import recalculate_contract, recalculate_project_control
	from erpnext.construcontrol.finance import recalculate_funding_source

	if doctype == "CC Funding Source":
		recalculate_funding_source(str(after["name"]))
	elif doctype == "CC Labor Contract":
		recalculate_contract(str(after["name"]))
	for project in {str(value) for value in (before.get("project"), after.get("project")) if value}:
		recalculate_project_control(project)


@frappe.whitelist(methods=["POST"])
def preview_record_correction(
	doctype: str,
	name: str,
	changes: Any,
	reason: str,
	evidence: str = "",
	authorization_token: str = "",
) -> dict[str, Any]:
	_require_token(authorization_token)
	return _prepare(doctype, name, changes, reason, evidence)


@frappe.whitelist(methods=["POST"])
def execute_record_correction(
	doctype: str,
	name: str,
	changes: Any,
	reason: str,
	evidence: str,
	preview_hash: str,
	authorization_token: str,
) -> dict[str, Any]:
	authorization = _require_token(authorization_token)
	payload = _prepare(doctype, name, changes, reason, evidence)
	if not secrets.compare_digest(str(preview_hash or ""), payload["preview_hash"]):
		frappe.throw(_("La vista previa cambió. Genérela nuevamente."))
	lock = frappe.cache.lock(
		f"construcontrol:record-correction:{doctype}:{name}", timeout=180, blocking_timeout=5
	)
	if not lock.acquire(blocking=True):
		frappe.throw(_("Existe otra corrección sobre este registro."))
	savepoint = f"cc_record_{frappe.generate_hash(length=12)}"
	frappe.db.savepoint(savepoint)
	try:
		doc = frappe.get_doc(doctype, name)
		schema = _schema(doctype)
		before = _snapshot(doc, schema)
		if before != payload["before"]:
			frappe.throw(_("El registro cambió después de la vista previa."))
		with _correction_context():
			for field, value in payload["changes"].items():
				if doc.meta.has_field(field):
					doc.set(field, value)
			doc.flags.ignore_construcontrol_audit = True
			doc.save(ignore_permissions=True)
			after = _snapshot(doc, schema)
			_recalculate(doctype, before, after)
			doc.reload()
			after = _snapshot(doc, schema)
			record_manual_event(
				module=payload["module"],
				action="ADMIN_CORRECT_RECORD",
				record_type=doctype,
				record_id=name,
				project=str(after.get("project") or "") or None,
				reason=payload["reason"],
				previous_state=before,
				next_state={
					**after,
					"impact": payload["impact"],
					"evidence": payload["evidence"],
					"authorization_id": authorization["authorization_id"],
				},
				origin="ADMIN_CORRECTION",
				correlation_id=authorization["authorization_id"],
			)
		frappe.db.release_savepoint(savepoint)
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise
	finally:
		try:
			lock.release()
		except Exception:
			pass
	return {
		"doctype": doctype,
		"name": name,
		"before": before,
		"after": after,
		"authorization_id": authorization["authorization_id"],
	}


def _payable_snapshot(expense_name: str) -> dict[str, Any]:
	if not frappe.db.exists("CC Expense Control", expense_name):
		frappe.throw(_("El gasto seleccionado no existe."))
	expense = frappe.get_doc("CC Expense Control", expense_name)
	meta = frappe.get_meta("CC Payable Control")
	fields = [
		field
		for field in (
			"name",
			"source_key",
			"expense_control",
			"supplier",
			"provider_name",
			"amount_hnl",
			"original_amount_hnl",
			"paid_amount_hnl",
			"balance_due_hnl",
			"payable_status",
			"status",
			"is_logically_deleted",
		)
		if field == "name" or meta.has_field(field)
	]
	names = set(
		frappe.get_all(
			"CC Payable Control", filters={"expense_control": expense_name}, pluck="name"
		)
	)
	source_key = f"expense-payable:{expense_name}"
	names.update(
		frappe.get_all("CC Payable Control", filters={"source_key": source_key}, pluck="name")
	)
	rows = [
		dict(frappe.db.get_value("CC Payable Control", name, fields, as_dict=True) or {})
		for name in sorted(names)
	]
	return {
		"expense": {
			"name": expense.name,
			"project": expense.get("project"),
			"supplier": expense.get("supplier"),
			"provider_name": expense.get("provider_name"),
			"calculated_total_hnl": expense.get("calculated_total_hnl")
			or expense.get("amount_hnl"),
			"paid_amount_hnl": expense.get("paid_amount_hnl"),
			"balance_due_hnl": expense.get("balance_due_hnl"),
			"payment_status": expense.get("payment_status"),
			"approval": expense.get("professional_approval_status"),
		},
		"payables": rows,
		"source_key": source_key,
		"duplicate_count": max(len(rows) - 1, 0),
	}


@frappe.whitelist(methods=["POST"])
def preview_payable_rebuild(
	expense_name: str,
	reason: str,
	authorization_token: str,
) -> dict[str, Any]:
	_require_token(authorization_token)
	payload = _payable_snapshot(str(expense_name or ""))
	payload["reason"] = _reason(reason)
	payload["preview_hash"] = _fingerprint(payload)
	return payload


@frappe.whitelist(methods=["POST"])
def execute_payable_rebuild(
	expense_name: str,
	reason: str,
	preview_hash: str,
	authorization_token: str,
) -> dict[str, Any]:
	authorization = _require_token(authorization_token)
	payload = _payable_snapshot(str(expense_name or ""))
	payload["reason"] = _reason(reason)
	payload["preview_hash"] = _fingerprint(payload)
	if not secrets.compare_digest(str(preview_hash or ""), payload["preview_hash"]):
		frappe.throw(_("La vista previa de la cuenta por pagar cambió."))
	lock = frappe.cache.lock(
		f"construcontrol:payable-rebuild:{expense_name}", timeout=120, blocking_timeout=5
	)
	if not lock.acquire(blocking=True):
		frappe.throw(_("Existe otra reconstrucción para este gasto."))
	savepoint = f"cc_payable_{frappe.generate_hash(length=12)}"
	frappe.db.savepoint(savepoint)
	try:
		with _correction_context():
			rows = payload["payables"]
			canonical = next(
				(row for row in rows if row.get("source_key") == payload["source_key"]), None
			)
			canonical = canonical or (rows[0] if rows else None)
			for row in rows:
				if canonical and row.get("name") == canonical.get("name"):
					continue
				updates = {
					"source_key": f"archived-payable:{row['name']}",
					"expense_control": None,
					"is_logically_deleted": 1,
					"status": "cancelled",
					"payable_status": "cancelled",
					"amount_hnl": 0,
					"balance_due_hnl": 0,
				}
				meta = frappe.get_meta("CC Payable Control")
				frappe.db.set_value(
					"CC Payable Control",
					row["name"],
					{key: value for key, value in updates.items() if meta.has_field(key)},
					update_modified=True,
				)
			if canonical:
				meta = frappe.get_meta("CC Payable Control")
				updates = {
					"source_key": payload["source_key"],
					"expense_control": expense_name,
					"is_logically_deleted": 0,
				}
				frappe.db.set_value(
					"CC Payable Control",
					canonical["name"],
					{key: value for key, value in updates.items() if meta.has_field(key)},
					update_modified=False,
				)
			from erpnext.construcontrol.expenses import sync_payable_from_expense

			expense = frappe.get_doc("CC Expense Control", expense_name)
			sync_payable_from_expense(expense)
			after = _payable_snapshot(expense_name)
			record_manual_event(
				module="FI02",
				action="ADMIN_REBUILD_PAYABLE",
				record_type="CC Expense Control",
				record_id=expense_name,
				project=str(expense.get("project") or "") or None,
				reason=payload["reason"],
				previous_state=payload,
				next_state={
					**after,
					"authorization_id": authorization["authorization_id"],
					"executed_at": now_datetime(),
				},
				origin="ADMIN_CORRECTION",
				correlation_id=authorization["authorization_id"],
			)
		frappe.db.release_savepoint(savepoint)
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise
	finally:
		try:
			lock.release()
		except Exception:
			pass
	return {**after, "authorization_id": authorization["authorization_id"]}


__all__ = [
	"execute_payable_rebuild",
	"execute_record_correction",
	"preview_payable_rebuild",
	"preview_record_correction",
]
