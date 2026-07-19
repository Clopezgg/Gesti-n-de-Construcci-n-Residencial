from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

from erpnext.construcontrol.construction import get_project_center

_ALLOWED_ROLES = {
    "System Manager",
    "ConstruControl Manager",
    "ConstruControl Auditor",
    "ConstruControl Operator",
    "ConstruControl Viewer",
}


def _require_access() -> None:
    if not (_ALLOWED_ROLES & set(frappe.get_roles())):
        frappe.throw(_("No tiene permisos para consultar el panel ejecutivo."), frappe.PermissionError)


def _filters(project: str | None = None) -> dict[str, Any]:
    filters: dict[str, Any] = {"is_logically_deleted": 0}
    if project:
        filters["project"] = project
    return filters


def _fields(doctype: str, requested: list[str]) -> list[str]:
    meta = frappe.get_meta(doctype)
    return [field for field in requested if field == "name" or meta.has_field(field)]


def _sum(rows: list[Any], fieldname: str) -> float:
    return sum(flt(row.get(fieldname)) for row in rows)


def _category_totals(rows: list[Any], key: str, amount: str) -> list[dict[str, Any]]:
    grouped: dict[str, float] = defaultdict(float)
    for row in rows:
        grouped[str(row.get(key) or "Sin clasificar")] += flt(row.get(amount))
    return [
        {"label": label, "amount_hnl": round(value, 2)}
        for label, value in sorted(grouped.items(), key=lambda item: item[1], reverse=True)
    ]


@frappe.whitelist()
def get_executive_dashboard(project: str | None = None) -> dict[str, Any]:
    _require_access()
    project_summary = get_project_center(project)
    project = project_summary.get("project")

    incomes = frappe.get_all(
        "CC Funding Source",
        filters=_filters(project),
        fields=_fields(
            "CC Funding Source",
            [
                "name", "amount_hnl", "gross_amount", "fee_amount", "net_amount_hnl",
                "spent_hnl", "pending_hnl", "available_hnl", "status", "income_type",
                "transaction_channel", "financial_institution", "reconciliation_status",
                "date_received", "sender",
            ],
        ),
        order_by="date_received desc, creation desc",
    )
    expenses = frappe.get_all(
        "CC Expense Control",
        filters=_filters(project),
        fields=_fields(
            "CC Expense Control",
            [
                "name", "amount_hnl", "paid_amount_hnl", "balance_due_hnl", "category",
                "subcategory", "provider_name", "payment_status", "financial_status",
                "professional_approval_status", "due_date", "posting_date", "phase",
            ],
        ),
        order_by="posting_date desc, creation desc",
    )
    payables = frappe.get_all(
        "CC Payable Control",
        filters=_filters(project),
        fields=_fields(
            "CC Payable Control",
            ["name", "expense_control", "provider_name", "invoice_number", "due_date", "balance_due_hnl", "payable_status"],
        ),
        order_by="due_date asc, creation desc",
    )
    contracts = frappe.get_all(
        "CC Labor Contract",
        filters=_filters(project),
        fields=["name", "contractor_name", "status", "project_value_hnl", "labor_value_hnl", "paid_hnl", "balance_hnl"],
    )
    materials = frappe.get_all(
        "CC Material Ledger",
        filters=_filters(project),
        fields=["name", "material_name", "current_qty", "unit", "stock_status", "low_stock_threshold", "unit_cost_hnl"],
    )

    received = sum(
        flt(row.get("net_amount_hnl") or row.get("amount_hnl"))
        for row in incomes
        if str(row.get("status") or "received") == "received"
    )
    spent = sum(
        flt(row.get("amount_hnl"))
        for row in expenses
        if row.get("financial_status") not in {"cancelled", "reimbursed"}
        and row.get("payment_status") in {"partially_paid", "paid"}
    )
    pending_expenses = sum(
        flt(row.get("balance_due_hnl") or row.get("amount_hnl"))
        for row in expenses
        if row.get("financial_status") not in {"cancelled", "reimbursed"}
        and row.get("payment_status") not in {"paid", "cancelled", "reimbursed"}
    )
    payable_balance = _sum(
        [row for row in payables if row.get("payable_status") not in {"paid", "cancelled", "reimbursed"}],
        "balance_due_hnl",
    )
    contract_value = sum(flt(row.project_value_hnl or row.labor_value_hnl) for row in contracts if str(row.status or "").lower() != "cancelled")
    contract_balance = sum(flt(row.balance_hnl) for row in contracts if str(row.status or "").lower() != "cancelled")
    low_stock = [row for row in materials if row.stock_status in {"low", "depleted"}]

    today_date = getdate(today())
    overdue = [
        row for row in payables
        if row.get("due_date") and getdate(row.due_date) < today_date
        and row.get("payable_status") not in {"paid", "cancelled", "reimbursed"}
    ]
    unreconciled = [
        row for row in incomes
        if row.get("reconciliation_status") not in {None, "", "reconciled"}
    ]

    alerts: list[dict[str, Any]] = []
    if flt(project_summary.get("available_budget_hnl")) < 0:
        alerts.append({"level": "critical", "title": "Presupuesto excedido", "message": _("Los compromisos superan el presupuesto actualizado.")})
    if overdue:
        alerts.append({"level": "critical", "title": "Cuentas vencidas", "message": _("Hay {0} cuentas por pagar vencidas.").format(len(overdue))})
    if low_stock:
        alerts.append({"level": "attention", "title": "Materiales críticos", "message": _("Hay {0} materiales con existencia baja o agotada.").format(len(low_stock))})
    if unreconciled:
        alerts.append({"level": "attention", "title": "Ingresos sin conciliar", "message": _("Hay {0} ingresos pendientes de conciliación.").format(len(unreconciled))})
    if project_summary.get("delayed_phase_count"):
        alerts.append({"level": "critical", "title": "Fases atrasadas", "message": _("Hay {0} fases fuera de fecha.").format(project_summary.get("delayed_phase_count"))})
    if not alerts:
        alerts.append({"level": "normal", "title": "Operación controlada", "message": _("No se detectaron alertas críticas con los datos actuales.")})

    recent_activity = frappe.get_all(
        "CC Audit Log",
        filters=_filters(project),
        fields=_fields("CC Audit Log", ["name", "posting_date", "action", "record_type", "record_id", "actor_name", "actor_role", "reason"]),
        order_by="creation desc",
        limit_page_length=12,
    )

    return {
        "project": project,
        "project_name": project_summary.get("project_name"),
        "projects": project_summary.get("projects", []),
        "financial": {
            "received_hnl": round(received, 2),
            "spent_hnl": round(spent, 2),
            "cash_available_hnl": round(received - spent, 2),
            "pending_expenses_hnl": round(pending_expenses, 2),
            "payable_balance_hnl": round(payable_balance, 2),
            "contract_value_hnl": round(contract_value, 2),
            "contract_balance_hnl": round(contract_balance, 2),
            "original_budget_hnl": project_summary.get("original_budget_hnl", 0),
            "updated_budget_hnl": project_summary.get("updated_budget_hnl", 0),
            "committed_hnl": project_summary.get("committed_hnl", 0),
            "actual_cost_hnl": project_summary.get("actual_cost_hnl", 0),
            "available_budget_hnl": project_summary.get("available_budget_hnl", 0),
        },
        "progress": {
            "physical_percent": project_summary.get("physical_progress_percent", 0),
            "financial_percent": project_summary.get("financial_progress_percent", 0),
            "schedule_status": project_summary.get("schedule_status", "on_track"),
            "phase_count": project_summary.get("phase_count", 0),
            "delayed_phase_count": project_summary.get("delayed_phase_count", 0),
            "at_risk_phase_count": project_summary.get("at_risk_phase_count", 0),
        },
        "counts": {
            "income_count": len(incomes),
            "expense_count": len(expenses),
            "contract_count": len(contracts),
            "payable_count": len(payables),
            "low_stock_count": len(low_stock),
            "overdue_count": len(overdue),
        },
        "charts": {
            "expenses_by_category": _category_totals(expenses, "category", "amount_hnl"),
            "income_by_channel": _category_totals(incomes, "transaction_channel", "amount_hnl"),
        },
        "alerts": alerts,
        "low_stock": low_stock[:8],
        "overdue_payables": overdue[:8],
        "recent_activity": recent_activity,
    }


__all__ = ["get_executive_dashboard"]
