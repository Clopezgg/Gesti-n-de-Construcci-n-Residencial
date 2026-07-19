from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

from erpnext.construcontrol.business_rules import expense_amounts
from erpnext.construcontrol.construction import get_project_center

_ALLOWED_ROLES = {
    "System Manager",
    "ConstruControl Manager",
    "ConstruControl Auditor",
    "ConstruControl Operator",
    "ConstruControl Viewer",
}

_LABELS = {
    "on_track": "En tiempo",
    "at_risk": "En riesgo",
    "delayed": "Atrasado",
    "completed": "Completado",
    "not_started": "Sin iniciar",
    "remittance": "Remesas",
    "deposit": "Depósitos",
    "transfer": "Transferencias",
    "cash": "Efectivo",
    "other": "Otros",
    "labor": "Mano de obra",
    "materials": "Materiales",
    "transport": "Transporte",
    "equipment": "Equipo y maquinaria",
    "services": "Servicios",
    "pending": "Pendiente",
    "partial": "Pago parcial",
    "paid": "Pagado",
    "overdue": "Vencido",
    "cancelled": "Anulado",
    "reimbursed": "Reembolsado",
    "CREATE": "Creación",
    "UPDATE": "Actualización",
    "SUBMIT": "Aprobación",
    "CANCEL": "Anulación",
    "DELETE": "Eliminación",
    "CC Project Profile": "Proyecto",
    "CC Expense Control": "Gasto",
    "CC Funding Source": "Ingreso",
    "CC Labor Contract": "Contrato",
    "CC Construction Phase": "Fase",
    "CC Material Ledger": "Material",
    "CC Inventory Movement": "Movimiento de inventario",
    "CC Progress Update": "Avance de obra",
    "CC User Access": "Acceso histórico",
}


def _label(value: Any) -> str:
    raw = str(value or "").strip()
    return _LABELS.get(raw, _LABELS.get(raw.lower(), raw.replace("_", " ").strip().capitalize() or "Sin clasificar"))


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
        grouped[str(row.get(key) or "other")] += flt(row.get(amount))
    return [
        {"code": code, "label": _label(code), "amount_hnl": round(value, 2)}
        for code, value in sorted(grouped.items(), key=lambda item: item[1], reverse=True)
        if value
    ]


def _recent_activity(project: str | None) -> list[dict[str, Any]]:
    rows = frappe.get_all(
        "CC Audit Log",
        filters=_filters(project),
        fields=_fields(
            "CC Audit Log",
            ["name", "posting_date", "action", "record_type", "record_id", "actor_name", "actor_role", "reason"],
        ),
        order_by="creation desc",
        limit_page_length=20,
    )
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for row in rows:
        key = (
            str(row.get("action") or ""),
            str(row.get("record_type") or ""),
            str(row.get("actor_name") or row.get("actor_role") or ""),
            str(row.get("posting_date") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(
            {
                **dict(row),
                "action_label": _label(row.get("action")),
                "record_type_label": _label(row.get("record_type")),
            }
        )
        if len(result) == 3:
            break
    return result


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
        if str(row.get("status") or "received").lower() not in {"cancelled", "rejected"}
    )
    recognized_expenses = paid_expenses = pending_expenses = 0.0
    for row in expenses:
        recognized, paid, pending = expense_amounts(
            row.get("amount_hnl"), row.get("payment_status"), row.get("financial_status"),
            row.get("paid_amount_hnl"), row.get("balance_due_hnl"),
        )
        recognized_expenses += recognized
        paid_expenses += paid
        pending_expenses += pending

    payable_rows = [row for row in payables if row.get("payable_status") not in {"paid", "cancelled", "reimbursed"}]
    payable_balance = _sum(payable_rows, "balance_due_hnl") or pending_expenses
    contract_value = sum(
        flt(row.get("project_value_hnl") or row.get("labor_value_hnl"))
        for row in contracts
        if str(row.get("status") or "").lower() != "cancelled"
    )
    contract_balance = sum(
        flt(row.get("balance_hnl"))
        for row in contracts
        if str(row.get("status") or "").lower() != "cancelled"
    )
    low_stock = [row for row in materials if row.get("stock_status") in {"low", "depleted"}]

    today_date = getdate(today())
    overdue = [
        {**dict(row), "payable_status_label": _label(row.get("payable_status"))}
        for row in payable_rows
        if row.get("due_date") and getdate(row.get("due_date")) < today_date
    ]
    unreconciled = [
        row for row in incomes
        if str(row.get("reconciliation_status") or "pending").lower() not in {"reconciled", "rejected"}
    ]

    alerts: list[dict[str, Any]] = []
    if flt(project_summary.get("available_budget_hnl")) < 0:
        alerts.append({"level": "critical", "title": "Presupuesto excedido", "message": _("Los compromisos superan el presupuesto actualizado."), "route": ["construcontrol-project-center"]})
    if overdue:
        count = len(overdue)
        alerts.append({"level": "critical", "title": "Cuentas vencidas", "message": _("{0} cuenta vencida.").format(count) if count == 1 else _("{0} cuentas vencidas.").format(count), "route": ["List", "CC Payable Control"]})
    if low_stock:
        count = len(low_stock)
        alerts.append({"level": "attention", "title": "Inventario crítico", "message": _("{0} material requiere atención.").format(count) if count == 1 else _("{0} materiales requieren atención.").format(count), "route": ["List", "CC Material Ledger"]})
    if unreconciled:
        count = len(unreconciled)
        alerts.append({"level": "attention", "title": "Ingresos sin conciliar", "message": _("{0} ingreso pendiente.").format(count) if count == 1 else _("{0} ingresos pendientes.").format(count), "route": ["List", "CC Funding Source"]})
    delayed_count = int(project_summary.get("delayed_phase_count") or 0)
    if delayed_count:
        alerts.append({"level": "critical", "title": "Fases atrasadas", "message": _("1 fase fuera de fecha.") if delayed_count == 1 else _("{0} fases fuera de fecha.").format(delayed_count), "route": ["List", "CC Construction Phase"]})
    if not alerts:
        alerts.append({"level": "normal", "title": "Operación controlada", "message": _("No se detectaron alertas críticas."), "route": ["construcontrol-project-center"]})

    schedule_status = str(project_summary.get("schedule_status") or "on_track")
    return {
        "project": project,
        "project_name": project_summary.get("project_name"),
        "projects": project_summary.get("projects", []),
        "financial": {
            "received_hnl": round(received, 2),
            "expense_total_hnl": round(recognized_expenses, 2),
            "paid_hnl": round(paid_expenses, 2),
            "cash_available_hnl": round(received - paid_expenses, 2),
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
            "schedule_status": schedule_status,
            "schedule_status_label": _label(schedule_status),
            "phase_count": project_summary.get("phase_count", 0),
            "delayed_phase_count": delayed_count,
            "at_risk_phase_count": project_summary.get("at_risk_phase_count", 0),
        },
        "counts": {
            "income_count": len(incomes),
            "expense_count": len(expenses),
            "contract_count": len(contracts),
            "payable_count": len(payable_rows),
            "low_stock_count": len(low_stock),
            "overdue_count": len(overdue),
        },
        "charts": {
            "expenses_by_category": _category_totals(expenses, "category", "amount_hnl"),
            "income_by_channel": _category_totals(incomes, "transaction_channel", "amount_hnl"),
        },
        "alerts": alerts[:4],
        "low_stock": low_stock[:3],
        "overdue_payables": overdue[:3],
        "recent_activity": _recent_activity(project),
    }


__all__ = ["get_executive_dashboard"]
