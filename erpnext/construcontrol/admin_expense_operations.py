from __future__ import annotations

import secrets
from typing import Any

import frappe
from frappe import _
from frappe.utils import now_datetime

from erpnext.construcontrol.admin_corrections import (
	_correction_context,
	_fingerprint,
	_prepare,
	_recalculate,
	_require_token,
	_snapshot,
)
from erpnext.construcontrol.audit import record_manual_event

_MAX_BATCH = 50
_TRACE_FIELDS = {
	"last_admin_correction_id",
	"last_admin_correction_at",
	"last_admin_correction_reason",
	"last_admin_correction_evidence",
	"payment_evidence",
	"rejection_reason",
}


def _parse_items(value: Any) -> list[dict[str, Any]]:
	if isinstance(value, str):
		try:
			value = frappe.parse_json(value)
		except Exception:
			frappe.throw(_("El lote de gastos no contiene JSON válido."))
	if not isinstance(value, list):
		frappe.throw(_("El lote debe contener una lista de gastos."))
	if not value or len(value) > _MAX_BATCH:
		frappe.throw(_("Seleccione entre 1 y {0} gastos por lote.").format(_MAX_BATCH))
	result: list[dict[str, Any]] = []
	seen: set[str] = set()
	for raw in value:
		if not isinstance(raw, dict):
			frappe.throw(_("Cada corrección del lote debe ser un objeto."))
		name = str(raw.get("expense_name") or raw.get("name") or "").strip()
		if not name or name in seen:
			frappe.throw(_("Cada gasto debe aparecer una sola vez en el lote."))
		seen.add(name)
		result.append(
			{
				"expense_name": name,
				"operation": str(raw.get("operation") or "correct"),
				"changes": raw.get("changes") or {},
			}
		)
	return result


def _apply_payload(payload: dict[str, Any], authorization_id: str) -> dict[str, Any]:
	doc = frappe.get_doc("CC Expense Control", payload["expense"])
	before = _snapshot(doc)
	if before != payload["before"]:
		frappe.throw(
			_("El gasto {0} cambió después de la vista previa.").format(frappe.bold(doc.name))
		)
	with _correction_context():
		for field, value in payload["proposed"].items():
			if field != "name" and doc.meta.has_field(field):
				doc.set(field, value)
		for field, value in {
			"last_admin_correction_id": authorization_id,
			"last_admin_correction_at": now_datetime(),
			"last_admin_correction_reason": payload["reason"],
			"last_admin_correction_evidence": payload["evidence"] or None,
		}.items():
			if doc.meta.has_field(field):
				doc.set(field, value)
		if payload["evidence"] and doc.meta.has_field("payment_evidence"):
			doc.payment_evidence = payload["evidence"]
		if payload["operation"] != "correct" and doc.meta.has_field("rejection_reason"):
			doc.rejection_reason = payload["reason"]
		write_fields = set(payload["proposed"]) | _TRACE_FIELDS
		updates = {
			field: doc.get(field)
			for field in write_fields
			if field != "name" and doc.meta.has_field(field) and before.get(field) != doc.get(field)
		}
		if updates:
			frappe.db.set_value("CC Expense Control", doc.name, updates, update_modified=True)
		doc.reload()
		after = _snapshot(doc)
		from erpnext.construcontrol.expenses import sync_payable_from_expense

		sync_payable_from_expense(doc)
		_recalculate(before, after)
		doc.reload()
		after = _snapshot(doc)
		record_manual_event(
			module="FI02",
			action=f"ADMIN_{payload['operation'].upper()}",
			record_type="CC Expense Control",
			record_id=doc.name,
			project=str(after.get("project") or "") or None,
			reason=payload["reason"],
			previous_state=before,
			next_state={
				**after,
				"evidence": payload["evidence"],
				"impact": payload["impact"],
				"authorization_id": authorization_id,
			},
			origin="ADMIN_CORRECTION",
			correlation_id=authorization_id,
		)
	return {"expense": doc.name, "before": before, "after": after, "impact": payload["impact"]}


@frappe.whitelist(methods=["POST"])
def execute_expense_correction(
	expense_name: str,
	operation: str,
	changes: Any,
	reason: str,
	evidence: str,
	preview_hash: str,
	authorization_token: str,
) -> dict[str, Any]:
	authorization = _require_token(authorization_token)
	payload = _prepare(str(expense_name or ""), operation, changes, reason, evidence)
	if not secrets.compare_digest(str(preview_hash or ""), payload["preview_hash"]):
		frappe.throw(_("La vista previa no coincide con la corrección solicitada."))
	lock = frappe.cache.lock(
		f"construcontrol:admin-correction:expense:{payload['expense']}",
		timeout=120,
		blocking_timeout=5,
	)
	if not lock.acquire(blocking=True):
		frappe.throw(_("Existe otra corrección sobre este gasto."))
	savepoint = f"cc_expense_{frappe.generate_hash(length=12)}"
	frappe.db.savepoint(savepoint)
	try:
		result = _apply_payload(payload, authorization["authorization_id"])
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
		**result,
		"operation": payload["operation"],
		"authorization_id": authorization["authorization_id"],
	}


@frappe.whitelist(methods=["POST"])
def preview_expense_batch(
	items: Any,
	reason: str,
	evidence: str = "",
	authorization_token: str = "",
) -> dict[str, Any]:
	_require_token(authorization_token)
	prepared = [
		_prepare(row["expense_name"], row["operation"], row["changes"], reason, evidence)
		for row in _parse_items(items)
	]
	payload = {
		"items": prepared,
		"count": len(prepared),
		"reason": prepared[0]["reason"],
		"evidence": evidence,
		"totals": {
			"recognized_delta_hnl": round(
				sum(row["impact"]["recognized_hnl"]["delta"] for row in prepared), 2
			),
			"paid_delta_hnl": round(
				sum(row["impact"]["paid_hnl"]["delta"] for row in prepared), 2
			),
			"pending_delta_hnl": round(
				sum(row["impact"]["pending_hnl"]["delta"] for row in prepared), 2
			),
		},
	}
	payload["preview_hash"] = _fingerprint(payload)
	return payload


@frappe.whitelist(methods=["POST"])
def execute_expense_batch(
	items: Any,
	reason: str,
	evidence: str,
	preview_hash: str,
	authorization_token: str,
) -> dict[str, Any]:
	authorization = _require_token(authorization_token)
	payload = preview_expense_batch(items, reason, evidence, authorization_token)
	if not secrets.compare_digest(str(preview_hash or ""), payload["preview_hash"]):
		frappe.throw(_("La vista previa del lote cambió. Genérela nuevamente."))
	locks: list[Any] = []
	for name in sorted(row["expense"] for row in payload["items"]):
		lock = frappe.cache.lock(
			f"construcontrol:admin-correction:expense:{name}", timeout=180, blocking_timeout=5
		)
		if not lock.acquire(blocking=True):
			for acquired in reversed(locks):
				acquired.release()
			frappe.throw(_("Existe otra corrección sobre uno de los gastos del lote."))
		locks.append(lock)
	savepoint = f"cc_expense_batch_{frappe.generate_hash(length=12)}"
	frappe.db.savepoint(savepoint)
	try:
		results = [
			_apply_payload(row, authorization["authorization_id"])
			for row in payload["items"]
		]
		record_manual_event(
			module="FI02",
			action="ADMIN_EXPENSE_BATCH",
			record_type="CC Expense Control",
			record_id=authorization["authorization_id"],
			reason=payload["reason"],
			previous_state={
				"count": payload["count"],
				"items": [row["before"] for row in payload["items"]],
			},
			next_state={
				"count": payload["count"],
				"results": results,
				"totals": payload["totals"],
				"evidence": evidence,
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
		for lock in reversed(locks):
			try:
				lock.release()
			except Exception:
				pass
	return {
		"count": len(results),
		"results": results,
		"totals": payload["totals"],
		"authorization_id": authorization["authorization_id"],
	}


__all__ = [
	"execute_expense_batch",
	"execute_expense_correction",
	"preview_expense_batch",
]
