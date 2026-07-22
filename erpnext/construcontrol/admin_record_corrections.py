from __future__ import annotations

import hashlib
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
			"treasury_exchange_rate",
			"reconciliation_status",
		},
		"derived": {
			"net_amount_hnl",
			"amount_hnl",
			"spent_hnl",
			"pending_hnl",
			"available_hnl",
			"projected_hnl",
		},
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
	fields = (
		set(schema["fields"])
		| set(schema["derived"])
		| {
			"name",
			"source_id",
			"source_key",
			"is_logically_deleted",
		}
	)
	return {field: doc.get(field) for field in sorted(fields) if doc.meta.has_field(field)}


def _session_fingerprint() -> str:
	value = str(getattr(frappe.session, "sid", "") or "")
	return hashlib.sha256(value.encode("utf-8")).hexdigest()[:20] if value else ""


def _lock_row(doctype: str, name: str) -> None:
	db_type = str(getattr(frappe.db, "db_type", "") or frappe.conf.get("db_type") or "").lower()
	table = f'"tab{doctype}"' if db_type == "postgres" else f"`tab{doctype}`"
	rows = frappe.db.sql(f"SELECT name FROM {table} WHERE name = %s FOR UPDATE", (name,))  # nosemgrep
	if not rows:
		frappe.throw(_("El registro seleccionado ya no existe."))


def _receipt(
	*,
	authorization_id: str,
	preview_hash: str,
	action: str,
	record_type: str,
	record_id: str,
) -> dict[str, Any] | None:
	rows = frappe.get_all(
		"CC Audit Log",
		filters={
			"correlation_id": authorization_id,
			"action": action,
			"record_type": record_type,
			"record_id": record_id,
		},
		fields=["next_state"],
		order_by="creation desc",
		limit=20,
	)
	for row in rows:
		try:
			state = frappe.parse_json(row.get("next_state") or "{}")
		except Exception:
			continue
		if isinstance(state, dict) and secrets.compare_digest(
			str(state.get("preview_hash") or ""), str(preview_hash or "")
		):
			result = state.get("result")
			return result if isinstance(result, dict) else state
	return None


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
	if not impact["changed_fields"]:
		frappe.throw(_("La vista previa no contiene cambios efectivos."))
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
	doctype = str(doctype or "").strip()
	name = str(name or "").strip()
	existing = _receipt(
		authorization_id=authorization["authorization_id"],
		preview_hash=str(preview_hash or ""),
		action="ADMIN_CORRECT_RECORD",
		record_type=doctype,
		record_id=name,
	)
	if existing:
		return {**existing, "idempotent": True, "operation_result": "ALREADY_APPLIED"}
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
		_lock_row(doctype, name)
		existing = _receipt(
			authorization_id=authorization["authorization_id"],
			preview_hash=str(preview_hash or ""),
			action="ADMIN_CORRECT_RECORD",
			record_type=doctype,
			record_id=name,
		)
		if existing:
			result = {**existing, "idempotent": True, "operation_result": "ALREADY_APPLIED"}
		else:
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
			result = {
				"doctype": doctype,
				"name": name,
				"before": before,
				"after": after,
				"impact": payload["impact"],
				"preview_hash": payload["preview_hash"],
				"status": "APPLIED",
				"authorization_id": authorization["authorization_id"],
			}
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
					"session_fingerprint": _session_fingerprint(),
					"preview_hash": payload["preview_hash"],
					"operation_result": "APPLIED",
					"result": result,
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
	return result


_PAYABLE_HISTORY_FIELDS = (
	"project",
	"supplier",
	"provider_name",
	"invoice_number",
	"posting_date",
	"due_date",
	"amount_hnl",
	"original_amount_hnl",
	"paid_amount_hnl",
	"balance_due_hnl",
	"payable_status",
	"status",
)


def _payable_fields() -> list[str]:
	meta = frappe.get_meta("CC Payable Control")
	return [
		field
		for field in (
			"name",
			"source_id",
			"source_key",
			"expense_control",
			*_PAYABLE_HISTORY_FIELDS,
			"is_logically_deleted",
		)
		if field == "name" or meta.has_field(field)
	]


def _payable_rows(names: list[str] | set[str]) -> list[dict[str, Any]]:
	fields = _payable_fields()
	return [
		dict(frappe.db.get_value("CC Payable Control", name, fields, as_dict=True) or {})
		for name in sorted({str(value) for value in names if value})
	]


def _payable_snapshot(expense_name: str) -> dict[str, Any]:
	if not frappe.db.exists("CC Expense Control", expense_name):
		frappe.throw(_("El gasto seleccionado no existe."))
	expense = frappe.get_doc("CC Expense Control", expense_name)
	names = set(frappe.get_all("CC Payable Control", filters={"expense_control": expense_name}, pluck="name"))
	source_key = f"expense-payable:{expense_name}"
	names.update(frappe.get_all("CC Payable Control", filters={"source_key": source_key}, pluck="name"))
	# Legacy migrations may have left the expense identity only in source_id.
	legacy_filters: dict[str, Any] = {"source_id": expense_name}
	if frappe.get_meta("CC Payable Control").has_field("is_logically_deleted"):
		legacy_filters["is_logically_deleted"] = 0
	names.update(frappe.get_all("CC Payable Control", filters=legacy_filters, pluck="name"))
	rows = _payable_rows(names)
	return {
		"expense": {
			"name": expense.name,
			"project": expense.get("project"),
			"supplier": expense.get("supplier"),
			"provider_name": expense.get("provider_name"),
			"calculated_total_hnl": expense.get("calculated_total_hnl") or expense.get("amount_hnl"),
			"paid_amount_hnl": expense.get("paid_amount_hnl"),
			"balance_due_hnl": expense.get("balance_due_hnl"),
			"payment_status": expense.get("payment_status"),
			"approval": expense.get("professional_approval_status"),
		},
		"payables": rows,
		"source_key": source_key,
		"duplicate_count": max(len(rows) - 1, 0),
	}


def _prepare_payable(expense_name: str, reason: str, evidence: str) -> dict[str, Any]:
	payload = _payable_snapshot(str(expense_name or "").strip())
	payload["reason"] = _reason(reason)
	payload["evidence"] = _evidence(evidence, True)
	payload["history_policy"] = "PRESERVE_FINANCIAL_HISTORY"
	payload["preview_hash"] = _fingerprint(payload)
	return payload


def _assert_payable_history_preserved(
	before_rows: list[dict[str, Any]], after_rows: list[dict[str, Any]]
) -> None:
	after_by_name = {str(row.get("name")): row for row in after_rows}
	for before in before_rows:
		after = after_by_name.get(str(before.get("name")))
		if not after:
			frappe.throw(_("Una cuenta por pagar histórica dejó de existir durante la corrección."))
		for field in _PAYABLE_HISTORY_FIELDS:
			if field in before and before.get(field) != after.get(field):
				frappe.throw(
					_("La corrección intentó alterar el campo histórico {0} de la cuenta {1}.").format(
						frappe.bold(field), frappe.bold(before.get("name"))
					)
				)


@frappe.whitelist(methods=["POST"])
def preview_payable_rebuild(
	expense_name: str,
	reason: str,
	evidence: str,
	authorization_token: str,
) -> dict[str, Any]:
	_require_token(authorization_token)
	return _prepare_payable(expense_name, reason, evidence)


@frappe.whitelist(methods=["POST"])
def execute_payable_rebuild(
	expense_name: str,
	reason: str,
	evidence: str,
	preview_hash: str,
	authorization_token: str,
) -> dict[str, Any]:
	authorization = _require_token(authorization_token)
	expense_name = str(expense_name or "").strip()
	existing = _receipt(
		authorization_id=authorization["authorization_id"],
		preview_hash=str(preview_hash or ""),
		action="ADMIN_REBUILD_PAYABLE",
		record_type="CC Expense Control",
		record_id=expense_name,
	)
	if existing:
		return {**existing, "idempotent": True, "operation_result": "ALREADY_APPLIED"}
	payload = _prepare_payable(expense_name, reason, evidence)
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
		_lock_row("CC Expense Control", expense_name)
		for row in payload["payables"]:
			_lock_row("CC Payable Control", str(row["name"]))
		current = _prepare_payable(expense_name, reason, evidence)
		if not secrets.compare_digest(str(preview_hash or ""), current["preview_hash"]):
			frappe.throw(_("La cuenta por pagar cambió después de la vista previa."))
		existing = _receipt(
			authorization_id=authorization["authorization_id"],
			preview_hash=str(preview_hash or ""),
			action="ADMIN_REBUILD_PAYABLE",
			record_type="CC Expense Control",
			record_id=expense_name,
		)
		if existing:
			result = {**existing, "idempotent": True, "operation_result": "ALREADY_APPLIED"}
		else:
			with _correction_context():
				rows = current["payables"]
				canonical = next(
					(row for row in rows if row.get("source_key") == current["source_key"]), None
				)
				canonical = canonical or (rows[0] if rows else None)
				archived_before = [
					row for row in rows if not canonical or row.get("name") != canonical.get("name")
				]
				meta = frappe.get_meta("CC Payable Control")
				for row in archived_before:
					updates = {
						"source_key": f"archived-payable:{row['name']}",
						"expense_control": None,
						"is_logically_deleted": 1,
					}
					frappe.db.set_value(
						"CC Payable Control",
						row["name"],
						{key: value for key, value in updates.items() if meta.has_field(key)},
						update_modified=True,
					)
				if canonical:
					updates = {
						"source_key": current["source_key"],
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
				archived_after = _payable_rows({str(row["name"]) for row in archived_before})
				_assert_payable_history_preserved(archived_before, archived_after)
				canonical_after = next(
					(row for row in after["payables"] if row.get("source_key") == current["source_key"]),
					None,
				)
				result = {
					**after,
					"canonical_payable": canonical_after.get("name") if canonical_after else None,
					"archived_payables": archived_after,
					"preview_hash": current["preview_hash"],
					"history_policy": current["history_policy"],
					"status": "APPLIED",
					"authorization_id": authorization["authorization_id"],
				}
				record_manual_event(
					module="FI02",
					action="ADMIN_REBUILD_PAYABLE",
					record_type="CC Expense Control",
					record_id=expense_name,
					project=str(expense.get("project") or "") or None,
					reason=current["reason"],
					previous_state=current,
					next_state={
						**after,
						"archived_payables": archived_after,
						"evidence": current["evidence"],
						"authorization_id": authorization["authorization_id"],
						"session_fingerprint": _session_fingerprint(),
						"preview_hash": current["preview_hash"],
						"operation_result": "APPLIED",
						"result": result,
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
	return result


__all__ = [
	"execute_payable_rebuild",
	"execute_record_correction",
	"preview_payable_rebuild",
	"preview_record_correction",
]
