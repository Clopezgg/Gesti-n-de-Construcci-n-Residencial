from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

_ALLOWED_ROLES = {
    "System Manager",
    "ConstruControl Manager",
    "ConstruControl Auditor",
    "ConstruControl Operator",
    "ConstruControl Viewer",
}


def _require_access() -> None:
    if not (_ALLOWED_ROLES & set(frappe.get_roles())):
        frappe.throw(_("No tiene permisos para consultar la gestión de obra."), frappe.PermissionError)


def _active_filters(project: str | None = None) -> dict[str, Any]:
    filters: dict[str, Any] = {"is_logically_deleted": 0}
    if project:
        filters["project"] = project
    return filters


def _safe_percent(value: float, total: float) -> float:
    return round((flt(value) / flt(total)) * 100, 2) if flt(total) else 0.0


def recalculate_project_control(project: str) -> dict[str, Any]:
    """Recalculate project and phase indicators from authoritative operational records."""
    if not project:
        frappe.throw(_("Seleccione un proyecto."))

    profile_name = frappe.db.get_value(
        "CC Project Profile",
        {"project": project, "is_logically_deleted": 0},
        "name",
    )
    if not profile_name:
        frappe.throw(_("El proyecto todavía no tiene un perfil ConstruControl."))

    phases = frappe.get_all(
        "CC Construction Phase",
        filters=_active_filters(project),
        fields=["name", "phase_name", "budget_hnl", "progress_percent", "target_end_date", "status", "milestone_date"],
    )
    expenses = frappe.get_all(
        "CC Expense Control",
        filters=_active_filters(project),
        fields=["phase", "amount_hnl", "balance_due_hnl", "payment_status", "financial_status"],
    )
    contracts = frappe.get_all(
        "CC Labor Contract",
        filters=_active_filters(project),
        fields=["phase", "project_value_hnl", "labor_value_hnl", "paid_hnl", "balance_hnl", "status"],
    )

    phase_actual: dict[str, float] = defaultdict(float)
    phase_pending: dict[str, float] = defaultdict(float)
    for row in expenses:
        if row.financial_status in {"cancelled", "reimbursed"}:
            continue
        amount = flt(row.amount_hnl)
        phase_actual[str(row.phase or "")] += amount
        if row.payment_status not in {"paid", "cancelled", "reimbursed"}:
            phase_pending[str(row.phase or "")] += flt(row.balance_due_hnl or amount)

    phase_contracts: dict[str, float] = defaultdict(float)
    for row in contracts:
        if str(row.status or "").lower() == "cancelled":
            continue
        phase_contracts[str(row.phase or "")] += flt(row.project_value_hnl or row.labor_value_hnl)

    today_date = getdate(today())
    weighted_progress_numerator = 0.0
    weighted_progress_denominator = 0.0
    total_budget = 0.0
    total_actual = sum(phase_actual.values())
    total_committed = 0.0
    delayed = 0
    at_risk = 0

    phase_rows: list[dict[str, Any]] = []
    for row in phases:
        budget = flt(row.budget_hnl)
        actual = phase_actual.get(row.name, 0.0)
        committed = max(actual + phase_pending.get(row.name, 0.0), phase_contracts.get(row.name, 0.0))
        available = budget - committed
        progress = flt(row.progress_percent)
        end_date = getdate(row.target_end_date) if row.target_end_date else None
        status = "completed" if progress >= 100 or str(row.status or "").lower() == "completed" else "on_track"
        if status != "completed" and end_date and end_date < today_date:
            status = "delayed"
            delayed += 1
        elif status != "completed" and (available < 0 or (end_date and (end_date - today_date).days <= 7 and progress < 80)):
            status = "at_risk"
            at_risk += 1
        elif progress <= 0:
            status = "not_started"

        frappe.db.set_value(
            "CC Construction Phase",
            row.name,
            {
                "committed_hnl": committed,
                "actual_cost_hnl": actual,
                "available_budget_hnl": available,
                "financial_progress_percent": _safe_percent(actual, budget),
                "schedule_status": status,
            },
            update_modified=False,
        )

        weight = budget if budget > 0 else 1.0
        weighted_progress_numerator += progress * weight
        weighted_progress_denominator += weight
        total_budget += budget
        total_committed += committed
        phase_rows.append(
            {
                "name": row.name,
                "phase_name": row.phase_name or row.name,
                "budget_hnl": round(budget, 2),
                "actual_cost_hnl": round(actual, 2),
                "committed_hnl": round(committed, 2),
                "available_budget_hnl": round(available, 2),
                "physical_progress_percent": round(progress, 2),
                "financial_progress_percent": _safe_percent(actual, budget),
                "schedule_status": status,
                "target_end_date": row.target_end_date,
                "milestone_date": row.milestone_date,
            }
        )

    profile = frappe.get_doc("CC Project Profile", profile_name)
    original_budget = flt(profile.get("original_budget_hnl"))
    updated_budget = flt(profile.get("updated_budget_hnl")) or total_budget or original_budget
    physical = round(weighted_progress_numerator / weighted_progress_denominator, 2) if weighted_progress_denominator else 0.0
    financial = _safe_percent(total_actual, updated_budget)
    variance = updated_budget - total_committed
    alert = "critical" if delayed or variance < 0 else "attention" if at_risk else "normal"
    schedule = "delayed" if delayed else "at_risk" if at_risk else "completed" if phases and physical >= 100 else "on_track"

    values = {
        "updated_budget_hnl": updated_budget,
        "committed_hnl": total_committed,
        "actual_cost_hnl": total_actual,
        "available_budget_hnl": updated_budget - total_committed,
        "physical_progress_percent": physical,
        "financial_progress_percent": financial,
        "budget_variance_hnl": variance,
        "schedule_status": schedule,
        "alert_level": alert,
    }
    for fieldname, value in values.items():
        if profile.meta.has_field(fieldname):
            profile.set(fieldname, value)
    profile.save(ignore_permissions=True)

    return {
        "project": project,
        "profile": profile.name,
        "project_name": profile.get("project_name") or project,
        "original_budget_hnl": round(original_budget, 2),
        "updated_budget_hnl": round(updated_budget, 2),
        "committed_hnl": round(total_committed, 2),
        "actual_cost_hnl": round(total_actual, 2),
        "available_budget_hnl": round(updated_budget - total_committed, 2),
        "physical_progress_percent": physical,
        "financial_progress_percent": financial,
        "budget_variance_hnl": round(variance, 2),
        "schedule_status": schedule,
        "alert_level": alert,
        "phase_count": len(phases),
        "delayed_phase_count": delayed,
        "at_risk_phase_count": at_risk,
        "phases": phase_rows,
    }


@frappe.whitelist()
def get_project_center(project: str | None = None) -> dict[str, Any]:
    _require_access()
    if not project:
        project = frappe.db.get_value(
            "CC Project Profile",
            {"is_current": 1, "is_logically_deleted": 0},
            "project",
        ) or frappe.db.get_value(
            "CC Project Profile",
            {"is_logically_deleted": 0},
            "project",
            order_by="modified desc",
        )
    if not project:
        return {"project": None, "projects": [], "phases": []}

    summary = recalculate_project_control(project)
    summary["projects"] = frappe.get_all(
        "CC Project Profile",
        filters={"is_logically_deleted": 0},
        fields=["project", "project_name", "is_current"],
        order_by="is_current desc, modified desc",
    )
    summary["contracts"] = frappe.get_all(
        "CC Labor Contract",
        filters=_active_filters(project),
        fields=["name", "contract_code", "contractor_name", "status", "project_value_hnl", "paid_hnl", "balance_hnl"],
        order_by="modified desc",
        limit_page_length=10,
    )
    summary["materials"] = frappe.get_all(
        "CC Material Ledger",
        filters=_active_filters(project),
        fields=["name", "material_name", "current_qty", "unit", "stock_status", "low_stock_threshold"],
        order_by="stock_status asc, material_name asc",
        limit_page_length=12,
    )
    summary["recent_progress"] = frappe.get_all(
        "CC Progress Update",
        filters=_active_filters(project),
        fields=["name", "posting_date", "title", "phase", "progress_percent", "quality", "responsible"],
        order_by="posting_date desc, creation desc",
        limit_page_length=10,
    )
    return summary


__all__ = ["get_project_center", "recalculate_project_control"]
