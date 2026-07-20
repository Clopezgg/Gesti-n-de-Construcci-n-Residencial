from __future__ import annotations

from typing import Any

import frappe

from erpnext.construcontrol.reporting_utils import _between, _fields


def _source_rows(start: Any, end: Any, scoped: dict[str, Any]) -> dict[str, list[Any]]:
    return {
        "funds": frappe.get_all(
            "CC Funding Source",
            filters={
                **scoped,
                "is_logically_deleted": 0,
                "date_received": _between(start, end),
            },
            fields=_fields(
                "CC Funding Source",
                [
                    "name",
                    "project",
                    "status",
                    "reconciliation_status",
                    "amount_hnl",
                    "net_amount_hnl",
                    "spent_hnl",
                    "pending_hnl",
                    "available_hnl",
                    "income_type",
                    "transaction_channel",
                    "date_received",
                ],
            ),
            order_by="date_received desc, creation desc",
        ),
        "expenses": frappe.get_all(
            "CC Expense Control",
            filters={
                **scoped,
                "is_logically_deleted": 0,
                "posting_date": _between(start, end),
            },
            fields=_fields(
                "CC Expense Control",
                [
                    "name",
                    "project",
                    "status",
                    "financial_status",
                    "payment_status",
                    "amount_hnl",
                    "paid_amount_hnl",
                    "balance_due_hnl",
                    "professional_approval_status",
                    "category",
                    "provider_name",
                    "posting_date",
                    "phase",
                ],
            ),
            order_by="posting_date desc, creation desc",
        ),
        "contracts": frappe.get_all(
            "CC Labor Contract",
            filters={**scoped, "is_logically_deleted": 0},
            fields=_fields(
                "CC Labor Contract",
                [
                    "name",
                    "project",
                    "status",
                    "project_value_hnl",
                    "labor_value_hnl",
                    "paid_hnl",
                    "balance_hnl",
                ],
            ),
        ),
        "phases": frappe.get_all(
            "CC Construction Phase",
            filters={**scoped, "is_logically_deleted": 0},
            fields=_fields(
                "CC Construction Phase",
                [
                    "name",
                    "project",
                    "phase_name",
                    "progress_percent",
                    "budget_hnl",
                    "actual_cost_hnl",
                    "committed_hnl",
                    "available_budget_hnl",
                    "schedule_status",
                    "status",
                ],
            ),
            order_by="phase_order asc, creation asc",
        ),
        "materials": frappe.get_all(
            "CC Material Ledger",
            filters={**scoped, "is_logically_deleted": 0},
            fields=_fields(
                "CC Material Ledger",
                [
                    "name",
                    "project",
                    "material_name",
                    "current_qty",
                    "unit_cost_hnl",
                    "stock_status",
                    "low_stock_threshold",
                ],
            ),
        ),
        "progress": frappe.get_all(
            "CC Progress Update",
            filters={
                **scoped,
                "is_logically_deleted": 0,
                "posting_date": _between(start, end),
            },
            fields=_fields(
                "CC Progress Update",
                [
                    "name",
                    "project",
                    "phase",
                    "progress_percent",
                    "quality",
                    "quality_status",
                    "status",
                    "posting_date",
                ],
            ),
            order_by="posting_date desc, creation desc",
        ),
        "closings": frappe.get_all(
            "CC Weekly Closing",
            filters={**scoped, "is_logically_deleted": 0, "week_end": ["<=", end]},
            fields=_fields(
                "CC Weekly Closing",
                [
                    "name",
                    "project",
                    "status",
                    "week_start",
                    "week_end",
                    "initial_balance_hnl",
                    "income_hnl",
                    "expense_hnl",
                    "pending_expense_hnl",
                    "final_balance_hnl",
                ],
            ),
            order_by="week_end desc, modified desc",
        ),
    }


__all__ = ["_source_rows"]
