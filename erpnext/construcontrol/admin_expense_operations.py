from __future__ import annotations

import hashlib
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


def _session_fingerprint() -> str:
	value = str(getattr(frappe.session, "sid", "") or "")
	return hashlib.sha256(value.encode("utf-8")).hexdigest()[:20] if value else ""


def _assert_effective_change(payload: dict[str, Any]) -> None:
	before = payload["before"]
	proposed = payload["proposed"]
	if not any(before.get(field) != value for field, value in proposed.items() if field != "name"):
		frappe.throw(_("La vista previa no contiene cambios efectivos."))


def _assert_recalculation_targets(payload: dict[str, Any]) -> None:
	projects = {str(value) for value in payload["impact"].get("projects", []) if value}
	for project in sorted(projects):
		if not frappe.db.exists(
			"CC Project Profile",
			{"project": project, "is_logically_deleted": 0},
		):
			frappe.throw(
				_(
					"El proyecto {0} no tiene un perfil ConstruControl activo; no puede recalcularse de forma segura."
				).format(frappe.bold(project))
			)


def _lock_expense_row(name: str) -> None:
	db_type = str(getattr(frappe.db, "db_type", "") or frappe.conf.get("db_type") or "").lower()
	table = '"tabCC Expense Control"' if db_type == "postgres" else "`tabCC Expense Control`"
	rows = frappe.db.sql(f"SELECT name FROM {table} WHERE name = %s FOR UPDATE", (name,))  # nosemgrep
	if not rows:
		frappe.throw(_("El gasto seleccionado ya no existe."))


def _receipt(
	*,
	authorization_id: str,
	preview_hash: str,
	action: str,
	record_id: str,
) -> dict[str, Any] | None:
	rows = frappe.get_all(
		"CC Audit Log",
		filters={
			"correlation_id": authorization_id,
			"action": action,
			"record_type": "CC Expense Control",
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


def _apply_payload(
	payload: dict[str, Any],
	authorization_id: str,
	preview_hash: str,
) -> dict[str, Any]:
	doc = frappe.get_doc("CC Expense Control", payload["expense"])
	before = _snapshot(doc)
	if before != payload["before"]:
		frappe.throw(_("El gasto {0} cambió después de la vista previa.").format(frappe.bold(doc.name)))
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
		result = {
			"expense": doc.name,
			"before": before,
			"after": after,
			"impact": payload["impact"],
			"status": "APPLIED",
			"preview_hash": preview_hash,
		}
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
				"session_fingerprint": _session_fingerprint(),
				"preview_hash": preview_hash,
				"result": result,
				"operation_result": "APPLIED",
			},
			origin="ADMIN_CORRECTION",
			correlation_id=authorization_id,
		)
	return result


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
	_assert_effective_change(payload)
	_assert_recalculation_targets(payload)
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
		_lock_expense_row(payload["expense"])
		action = f"ADMIN_{payload['operation'].upper()}"
		existing = _receipt(
			authorization_id=authorization["authorization_id"],
			preview_hash=payload["preview_hash"],
			action=action,
			record_id=payload["expense"],
		)
		if existing:
			result = {**existing, "idempotent": True, "operation_result": "ALREADY_APPLIED"}
		else:
			result = _apply_payload(
				payload,
				authorization["authorization_id"],
				payload["preview_hash"],
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
	for row in prepared:
		_assert_effective_change(row)
		_assert_recalculation_targets(row)
	payload = {
		"items": prepared,
		"count": len(prepared),
		"reason": prepared[0]["reason"],
		"evidence": evidence,
		"totals": {
			"recognized_delta_hnl": round(
				sum(row["impact"]["recognized_hnl"]["delta"] for row in prepared), 2
			),
			"paid_delta_hnl": round(sum(row["impact"]["paid_hnl"]["delta"] for row in prepared), 2),
			"pending_delta_hnl": round(sum(row["impact"]["pending_hnl"]["delta"] for row in prepared), 2),
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
		for name in sorted(row["expense"] for row in payload["items"]):
			_lock_expense_row(name)
		existing = _receipt(
			authorization_id=authorization["authorization_id"],
			preview_hash=payload["preview_hash"],
			action="ADMIN_EXPENSE_BATCH",
			record_id=authorization["authorization_id"],
		)
		if existing:
			results = existing.get("results") or []
			batch_result = {**existing, "idempotent": True, "operation_result": "ALREADY_APPLIED"}
		else:
			results = [
				_apply_payload(row, authorization["authorization_id"], row["preview_hash"])
				for row in payload["items"]
			]
			batch_result = {
				"count": len(results),
				"results": results,
				"totals": payload["totals"],
				"preview_hash": payload["preview_hash"],
				"status": "APPLIED",
			}
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
					"session_fingerprint": _session_fingerprint(),
					"preview_hash": payload["preview_hash"],
					"result": batch_result,
					"operation_result": "APPLIED",
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
		**batch_result,
		"authorization_id": authorization["authorization_id"],
	}


__all__ = [
	"execute_expense_batch",
	"execute_expense_correction",
	"preview_expense_batch",
]
