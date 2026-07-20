from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import flt, now_datetime

from erpnext.construcontrol.access import (
    accessible_project_profiles,
    assert_project_access,
    project_filter,
    require_construcontrol_access,
)
from erpnext.construcontrol.business_rules import (
    expense_amounts,
    recognized_funding_amount,
)
from erpnext.construcontrol.reporting_sources import _source_rows
from erpnext.construcontrol.reporting_utils import (
    _EXPORT_ROLES,
    _READER_ROLES,
    _WRITER_ROLES,
    _active_contract,
    _fields,
    _full_name,
    _period,
    _require,
    _role_label,
    _weighted_progress,
)


def _build_summary(
    rows: dict[str, list[Any]], project: str | None, start: Any, end: Any
) -> dict[str, Any]:
    funds = rows["funds"]
    expenses = rows["expenses"]
    contracts = rows["contracts"]
    phases = rows["phases"]
    materials = rows["materials"]
    progress_rows = rows["progress"]
    closings = rows["closings"]

    received = round(
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
    categories: dict[str, float] = {}
    providers: dict[str, float] = {}
    income_channels: dict[str, float] = {}
    for row in funds:
        amount = recognized_funding_amount(
            row.get("net_amount_hnl") or row.get("amount_hnl"),
            row.get("status"),
            row.get("reconciliation_status"),
        )
        if amount:
            channel = str(
                row.get("transaction_channel") or row.get("income_type") or "other"
            )
            income_channels[channel] = round(
                income_channels.get(channel, 0.0) + amount, 2
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
        if row_recognized:
            category = str(row.get("category") or "other")
            provider = str(row.get("provider_name") or "Sin proveedor")
            categories[category] = round(
                categories.get(category, 0.0) + row_recognized, 2
            )
            providers[provider] = round(
                providers.get(provider, 0.0) + row_recognized, 2
            )

    active_contracts = [row for row in contracts if _active_contract(row)]
    contracted = round(
        sum(
            flt(row.get("project_value_hnl") or row.get("labor_value_hnl"))
            for row in active_contracts
        ),
        2,
    )
    contract_paid = round(sum(flt(row.get("paid_hnl")) for row in active_contracts), 2)
    contract_balance = round(
        sum(flt(row.get("balance_hnl")) for row in active_contracts), 2
    )
    phase_budget = round(sum(flt(row.get("budget_hnl")) for row in phases), 2)
    phase_actual = round(sum(flt(row.get("actual_cost_hnl")) for row in phases), 2)
    phase_committed = round(sum(flt(row.get("committed_hnl")) for row in phases), 2)
    inventory_value = round(
        sum(
            flt(row.get("current_qty")) * flt(row.get("unit_cost_hnl"))
            for row in materials
        ),
        2,
    )
    low_stock = [
        row
        for row in materials
        if str(row.get("stock_status") or "") in {"low", "depleted"}
    ]
    quality_issues = [
        row
        for row in progress_rows
        if str(row.get("quality_status") or row.get("quality") or "").strip().casefold()
        in {"failed", "rejected", "non_compliant", "attention", "poor"}
    ]
    closed_closings = [
        row for row in closings if str(row.get("status") or "").casefold() == "closed"
    ]
    latest_closing = dict(closed_closings[0]) if closed_closings else None

    totals = {
        "received_hnl": received,
        "recognized_expense_hnl": round(recognized, 2),
        "spent_hnl": round(paid, 2),
        "pending_hnl": round(pending, 2),
        "available_hnl": round(received - paid, 2),
        "projected_hnl": round(received - recognized, 2),
        "contracted_hnl": contracted,
        "contract_paid_hnl": contract_paid,
        "contract_balance_hnl": contract_balance,
        "phase_budget_hnl": phase_budget,
        "phase_actual_hnl": phase_actual,
        "phase_committed_hnl": phase_committed,
        "phase_available_hnl": round(phase_budget - phase_committed, 2),
        "inventory_value_hnl": inventory_value,
        "overall_progress": _weighted_progress(phases),
    }
    return {
        "period": {"date_from": str(start), "date_to": str(end)},
        "project": project,
        "totals": totals,
        "counts": {
            "funds": len(funds),
            "expenses": len(expenses),
            "contracts": len(active_contracts),
            "phases": len(phases),
            "materials": len(materials),
            "low_stock": len(low_stock),
            "progress_updates": len(progress_rows),
            "quality_issues": len(quality_issues),
            "closings": len(closed_closings),
        },
        "expense_categories": [
            {"label": label, "amount_hnl": amount}
            for label, amount in sorted(
                categories.items(), key=lambda item: item[1], reverse=True
            )
        ],
        "income_channels": [
            {"label": label, "amount_hnl": amount}
            for label, amount in sorted(
                income_channels.items(), key=lambda item: item[1], reverse=True
            )
        ],
        "providers": [
            {"label": label, "amount_hnl": amount}
            for label, amount in sorted(
                providers.items(), key=lambda item: item[1], reverse=True
            )[:10]
        ],
        "phases": [dict(row) for row in phases],
        "low_stock": [dict(row) for row in low_stock[:10]],
        "quality_issues": [dict(row) for row in quality_issues[:10]],
        "latest_closing": latest_closing,
        "drill_down": {
            "funds": ["List", "CC Funding Source"],
            "expenses": ["List", "CC Expense Control"],
            "contracts": ["List", "CC Labor Contract"],
            "inventory": ["List", "CC Material Ledger"],
            "quality": ["List", "CC Progress Update"],
            "closings": ["List", "CC Weekly Closing"],
        },
    }


@frappe.whitelist()
def get_reporting_summary(
    date_from: str | None = None,
    date_to: str | None = None,
    project: str | None = None,
) -> dict[str, Any]:
    _require(
        _READER_ROLES, "No tiene permiso para consultar reportes de ConstruControl."
    )
    require_construcontrol_access()
    start, end = _period(date_from, date_to)
    scoped = project_filter(project)
    resolved_project = assert_project_access(project) if project else None
    summary = _build_summary(
        _source_rows(start, end, scoped), resolved_project, start, end
    )
    summary["generated_at"] = str(now_datetime())
    summary["generated_by"] = {
        "email": frappe.session.user,
        "name": _full_name(frappe.session.user),
        "role": _role_label(),
    }
    return summary


@frappe.whitelist()
def get_reporting_context() -> dict[str, Any]:
    _require(
        _READER_ROLES, "No tiene permiso para consultar reportes de ConstruControl."
    )
    require_construcontrol_access()
    contact_filters: dict[str, Any] = {"is_logically_deleted": 0}
    if frappe.get_meta("CC Notification Contact").has_field("project"):
        contact_filters.update(project_filter())
    contacts = frappe.get_all(
        "CC Notification Contact",
        filters=contact_filters,
        fields=_fields(
            "CC Notification Contact",
            [
                "name",
                "project",
                "title",
                "contact_name",
                "phone",
                "authorized",
                "active",
            ],
        ),
        order_by="title asc",
        limit_page_length=200,
    )
    return {
        "projects": accessible_project_profiles(),
        "contacts": [
            dict(row)
            for row in contacts
            if int(row.get("active") if row.get("active") is not None else 1)
            and int(row.get("authorized") or 0)
        ],
        "can_export": bool(set(frappe.get_roles()) & _EXPORT_ROLES),
        "can_generate": bool(set(frappe.get_roles()) & _WRITER_ROLES),
    }


__all__ = ["get_reporting_context", "get_reporting_summary"]
