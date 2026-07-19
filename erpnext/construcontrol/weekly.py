from __future__ import annotations

import hashlib
import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, now_datetime

from erpnext.construcontrol.access import assert_project_access, require_construcontrol_access
from erpnext.construcontrol.business_rules import expense_amounts, recognized_funding_amount

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
    filters: dict[str, Any] = {**_filters(project), "is_logically_deleted": 0, "week_end": ["<", start]}
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
            "status", "financial_status", "payment_status", "amount_hnl",
            "paid_amount_hnl", "balance_due_hnl", "professional_approval_status",
        ],
    )
    movements = frappe.get_all(
        "CC Inventory Movement",
        filters={**_filters(project), "is_logically_deleted": 0, "posting_date": ["between", [start, end]]},
        fields=["movement_type", "quantity", "material"],
    )
    progress = frappe.get_all(
        "CC Progress Update",
        filters={**_filters(project), "is_logically_deleted": 0, "posting_date": ["between", [start, end]]},
        fields=["name", "progress_percent", "phase"],
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

    paid = round(paid, 2)
    pending = round(pending, 2)
    initial = _previous_balance(project, start)
    final = round(initial + income - paid, 2)

    pending_items: list[str] = []
    if pending:
        pending_items.append(f"Gastos pendientes por L {pending:,.2f}")
    open_approvals = frappe.db.count(
        "CC Approval Request",
        {**_filters(project), "is_logically_deleted": 0, "status": ["not in", ["approved", "rejected", "cancelled"]]},
    )
    if open_approvals:
        pending_items.append(f"{open_approvals} aprobación(es) pendiente(s)")

    return {
        "initial_balance_hnl": initial,
        "income_hnl": income,
        "recognized_expense_hnl": round(recognized, 2),
        "expense_hnl": paid,
        "pending_expense_hnl": pending,
        "final_balance_hnl": final,
        "inventory_movement_count": len(movements),
        "progress_update_count": len(progress),
        "pending_items": pending_items,
    }


@frappe.whitelist()
def preview_weekly_closing(
    week_start: str,
    week_end: str | None = None,
    project: str | None = None,
) -> dict[str, Any]:
    _require_writer()
    project = _project(project)
    start, end = _period(week_start, week_end)
    return {"week_start": str(start), "week_end": str(end), "project": project, "snapshot": _snapshot(project, start, end)}


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

    existing = frappe.db.get_value(
        "CC Weekly Closing",
        {**_filters(project), "week_start": start, "week_end": end, "is_logically_deleted": 0},
        "name",
    )
    if existing:
        frappe.throw(_("Ya existe un cierre activo para el mismo proyecto y período: {0}").format(existing))

    snapshot = _snapshot(project, start, end)
    user = frappe.session.user
    identity = f"{project}|{start}|{end}"
    source_key = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:40]
    title = f"CL01 · Cierre {start} a {end}"
    values = {
        "doctype": "CC Weekly Closing",
        "source_key": source_key,
        "source_id": source_key,
        "project": project,
        "code": f"CL01-{start.strftime('%Y%m%d')}",
        "title": title,
        "status": normalized_status,
        "posting_date": start,
        "description": "Cierre calculado desde los movimientos vivos de ConstruControl.",
        "week_start": start,
        "week_end": end,
        "initial_balance_hnl": snapshot["initial_balance_hnl"],
        "income_hnl": snapshot["income_hnl"],
        "expense_hnl": snapshot["expense_hnl"],
        "final_balance_hnl": snapshot["final_balance_hnl"],
        "pending_expense_hnl": snapshot["pending_expense_hnl"],
        "inventory_movement_count": snapshot["inventory_movement_count"],
        "progress_update_count": snapshot["progress_update_count"],
        "pending_items_json": json.dumps(snapshot["pending_items"], ensure_ascii=False),
        "generated_at": now_datetime(),
        "generated_by_name": _full_name(user),
        "generated_by_email": user,
        "generated_by_role": _role_label(),
        "payload_json": json.dumps(snapshot, ensure_ascii=False, sort_keys=True, default=str),
        "is_logically_deleted": 0,
    }
    allowed = {field.fieldname for field in frappe.get_meta("CC Weekly Closing").fields}
    document = frappe.get_doc({key: value for key, value in values.items() if key == "doctype" or key in allowed})
    document.insert()
    return {"name": document.name, "title": title, "snapshot": snapshot}
