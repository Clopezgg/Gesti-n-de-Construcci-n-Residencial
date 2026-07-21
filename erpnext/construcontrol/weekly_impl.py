from __future__ import annotations

import hashlib
import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, now_datetime

from erpnext.construcontrol.access import (
	assert_project_access,
	require_construcontrol_access,
)
from erpnext.construcontrol.business_rules import expense_amounts, recognized_funding_amount
from erpnext.construcontrol.closing import closing_snapshot, snapshot_digest

_ROLE_LABELS = (
	("System Manager", "ADMIN"),
	("ConstruControl Manager", "MANAGER"),
	("ConstruControl Operator", "OPERATOR"),
)


def _require_writer() -> None:
	require_construcontrol_access(write=True)


def _role_label() -> str:
	roles = set(frappe.get_roles())
	for role, label in _ROLE_LABELS:
		if role in roles:
			return label
	return "USER"


def _full_name(user: str) -> str:
	return str(frappe.db.get_value("User", user, "full_name") or user)


def _period(week_start: str, week_end: str | None) -> tuple[Any, Any]:
	start = getdate(week_start)
	end = getdate(week_end) if week_end else add_days(start, 6)
	if end < start:
		frappe.throw(_("La fecha final del cierre no puede ser anterior a la fecha inicial."))
	if (end - start).days > 13:
		frappe.throw(_("El cierre no puede abarcar más de catorce días."))
	return start, end


def _project(project: str | None) -> str:
	if not str(project or "").strip():
		frappe.throw(_("Seleccione el proyecto del cierre semanal."))
	return assert_project_access(str(project), write=True)


def _filters(project: str) -> dict[str, Any]:
	return {"project": project}


def _previous_balance(project: str, start: Any) -> float:
	filters: dict[str, Any] = {
		**_filters(project),
		"is_logically_deleted": 0,
		"status": "closed",
		"week_end": ["<", start],
	}
	return flt(
		frappe.db.get_value(
			"CC Weekly Closing",
			filters,
			"final_balance_hnl",
			order_by="week_end desc, modified desc",
		)
	)


def _snapshot(project: str, start: Any, end: Any) -> dict[str, Any]:
	funds = frappe.get_all(
		"CC Funding Source",
		filters={**_filters(project), "is_logically_deleted": 0, "date_received": ["between", [start, end]]},
		fields=["status", "reconciliation_status", "amount_hnl", "net_amount_hnl"],
	)
	expenses = frappe.get_all(
		"CC Expense Control",
		filters={**_filters(project), "is_logically_deleted": 0, "posting_date": ["between", [start, end]]},
		fields=[
			"status",
			"financial_status",
			"payment_status",
			"amount_hnl",
			"paid_amount_hnl",
			"balance_due_hnl",
			"professional_approval_status",
		],
	)
	movement_count = frappe.db.count(
		"CC Inventory Movement",
		{**_filters(project), "is_logically_deleted": 0, "posting_date": ["between", [start, end]]},
	)
	progress_count = frappe.db.count(
		"CC Progress Update",
		{**_filters(project), "is_logically_deleted": 0, "posting_date": ["between", [start, end]]},
	)

	income = round(
		sum(
			recognized_funding_amount(
				row.get("net_amount_hnl") or row.get("amount_hnl"),
				row.get("status"),
				row.get("reconciliation_status"),
			)
			for row in funds
		),
		2,
	)
	recognized = paid = pending = 0.0
	for row in expenses:
		row_recognized, row_paid, row_pending = expense_amounts(
			row.get("amount_hnl"),
			row.get("payment_status"),
			row.get("financial_status"),
			row.get("paid_amount_hnl"),
			row.get("balance_due_hnl"),
			row.get("professional_approval_status"),
		)
		recognized += row_recognized
		paid += row_paid
		pending += row_pending

	open_approvals = frappe.db.count(
		"CC Approval Request",
		{
			**_filters(project),
			"is_logically_deleted": 0,
			"status": ["not in", ["approved", "rejected", "cancelled"]],
		},
	)
	unreconciled = sum(
		1
		for row in funds
		if str(row.get("reconciliation_status") or "pending").lower() not in {"verified", "reconciled"}
	)
	quality_failures = frappe.db.count(
		"CC Progress Update",
		{
			**_filters(project),
			"is_logically_deleted": 0,
			"posting_date": ["between", [start, end]],
			"quality_status": ["in", ["failed", "corrective"]],
			"incident_status": ["!=", "resolved"],
		},
	)
	try:
		return closing_snapshot(
			initial_balance=_previous_balance(project, start),
			income=income,
			recognized_expense=recognized,
			paid_expense=paid,
			pending_expense=pending,
			inventory_movements=movement_count,
			progress_updates=progress_count,
			quality_failures=quality_failures,
			open_approvals=open_approvals,
			unreconciled_funds=unreconciled,
		)
	except ValueError as exc:
		frappe.throw(_(str(exc)))


def _document_values(
	project: str,
	start: Any,
	end: Any,
	status: str,
	snapshot: dict[str, Any],
) -> dict[str, Any]:
	user = frappe.session.user
	identity = f"{project}|{start}|{end}"
	source_key = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:40]
	title = f"CL01 · Cierre {start} a {end}"
	return {
		"source_key": source_key,
		"source_id": source_key,
		"project": project,
		"code": f"CL01-{start.strftime('%Y%m%d')}",
		"title": title,
		"status": status,
		"posting_date": start,
		"description": "Cierre calculado desde los movimientos vivos de ConstruControl.",
		"week_start": start,
		"week_end": end,
		"initial_balance_hnl": snapshot["initial_balance_hnl"],
		"income_hnl": snapshot["income_hnl"],
		"recognized_expense_hnl": snapshot["recognized_expense_hnl"],
		"expense_hnl": snapshot["expense_hnl"],
		"pending_expense_hnl": snapshot["pending_expense_hnl"],
		"committed_hnl": snapshot["committed_hnl"],
		"final_balance_hnl": snapshot["final_balance_hnl"],
		"projected_balance_hnl": snapshot["projected_balance_hnl"],
		"inventory_movement_count": snapshot["inventory_movement_count"],
		"progress_update_count": snapshot["progress_update_count"],
		"quality_failure_count": snapshot["quality_failure_count"],
		"reconciliation_status": snapshot["reconciliation_status"],
		"pending_items_json": json.dumps(snapshot["pending_items"], ensure_ascii=False),
		"snapshot_digest": snapshot_digest(snapshot),
		"generated_at": now_datetime(),
		"generated_by_name": _full_name(user),
		"generated_by_email": user,
		"generated_by_role": _role_label(),
		"payload_json": json.dumps(snapshot, ensure_ascii=False, sort_keys=True, default=str),
		"is_logically_deleted": 0,
	}


def _assign(document: Any, values: dict[str, Any]) -> None:
	allowed = {field.fieldname for field in document.meta.fields}
	for key, value in values.items():
		if key in allowed:
			document.set(key, value)


@frappe.whitelist()
def preview_weekly_closing(
	week_start: str,
	week_end: str | None = None,
	project: str | None = None,
) -> dict[str, Any]:
	_require_writer()
	project = _project(project)
	start, end = _period(week_start, week_end)
	snapshot = _snapshot(project, start, end)
	return {
		"week_start": str(start),
		"week_end": str(end),
		"project": project,
		"snapshot": snapshot,
		"snapshot_digest": snapshot_digest(snapshot),
	}


@frappe.whitelist(methods=["POST"])
def create_weekly_closing(
	week_start: str,
	week_end: str | None = None,
	project: str | None = None,
	status: str = "draft",
) -> dict[str, Any]:
	_require_writer()
	project = _project(project)
	start, end = _period(week_start, week_end)
	normalized_status = str(status or "draft").strip().casefold()
	if normalized_status not in {"draft", "closed"}:
		frappe.throw(_("Estado de cierre no válido."))
	if normalized_status == "closed":
		require_construcontrol_access(manage=True)

	snapshot = _snapshot(project, start, end)
	values = _document_values(project, start, end, normalized_status, snapshot)
	existing = frappe.db.get_value(
		"CC Weekly Closing",
		{**_filters(project), "week_start": start, "week_end": end, "is_logically_deleted": 0},
		["name", "status", "snapshot_digest"],
		as_dict=True,
	)
	if existing:
		if existing.status == normalized_status and existing.snapshot_digest == values["snapshot_digest"]:
			return {
				"name": existing.name,
				"title": values["title"],
				"snapshot": snapshot,
				"idempotent": True,
			}
		if str(existing.status or "draft").lower() != "draft":
			frappe.throw(
				_("El cierre está cerrado y sus datos cambiaron; debe reabrirse antes de recalcularlo.")
			)
		document = frappe.get_doc("CC Weekly Closing", existing.name)
		_assign(document, values)
		document.save()
		return {
			"name": document.name,
			"title": values["title"],
			"snapshot": snapshot,
			"idempotent": False,
			"refreshed": True,
		}

	overlap = frappe.db.get_value(
		"CC Weekly Closing",
		{
			**_filters(project),
			"is_logically_deleted": 0,
			"week_start": ["<=", end],
			"week_end": [">=", start],
		},
		"name",
	)
	if overlap:
		frappe.throw(_("El período se superpone con otro cierre activo: {0}").format(overlap))

	document = frappe.new_doc("CC Weekly Closing")
	_assign(document, values)
	document.insert()
	return {
		"name": document.name,
		"title": values["title"],
		"snapshot": snapshot,
		"idempotent": False,
		"created": True,
	}


@frappe.whitelist(methods=["POST"])
def reopen_weekly_closing(name: str, reason: str) -> dict[str, Any]:
	require_construcontrol_access(manage=True)
	document = frappe.get_doc("CC Weekly Closing", str(name or "").strip())
	assert_project_access(document.project, write=True)
	reason = str(reason or "").strip()
	if document.status != "closed":
		frappe.throw(_("Solo se puede reabrir un cierre cerrado."))
	if not reason:
		frappe.throw(_("Indique el motivo de reapertura."))
	document.status = "draft"
	if document.meta.has_field("reopened_by"):
		document.reopened_by = frappe.session.user
	if document.meta.has_field("reopened_at"):
		document.reopened_at = now_datetime()
	if document.meta.has_field("reopen_reason"):
		document.reopen_reason = reason
	document.save()
	return {"name": document.name, "status": document.status, "reopened": True}
