from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from erpnext.construcontrol import executive_impl as _implementation
from erpnext.construcontrol.reporting import get_reporting_summary

# Explicit BI01 contract fields kept on the public service surface. The imported
# get_reporting_summary is the canonical source used by the implementation.
EXECUTIVE_CONTRACT_FIELDS = (
    "received_hnl",
    "expense_total_hnl",
    "paid_hnl",
    "cash_available_hnl",
    "payable_balance_hnl",
    "updated_budget_hnl",
    "committed_hnl",
    "available_budget_hnl",
    "physical_percent",
    "financial_percent",
    "schedule_status_label",
    "action_label",
    "record_type_label",
    "recent_activity",
    'counts["quality_issues"]',
    'counts["closings"]',
)


def _append_missing_actionable_alerts(result: dict[str, Any]) -> None:
    project = str(result.get("project") or "").strip()
    if not project:
        return

    alerts = list(result.get("alerts") or [])
    titles = {str(alert.get("title") or "") for alert in alerts}

    delayed_count = int((result.get("progress") or {}).get("delayed_phase_count") or 0)
    if delayed_count and "Fases atrasadas" not in titles:
        alerts.append(
            {
                "level": "attention",
                "title": "Fases atrasadas",
                "message": _("{0} fase(s) presentan retraso.").format(delayed_count),
                "route": ["List", "CC Construction Phase"],
            }
        )

    unreconciled_count = frappe.db.count(
        "CC Funding Source",
        {
            "project": project,
            "is_logically_deleted": 0,
            "reconciliation_status": ["not in", ["verified", "reconciled"]],
        },
    )
    if unreconciled_count and "Ingresos sin conciliar" not in titles:
        alerts.append(
            {
                "level": "attention",
                "title": "Ingresos sin conciliar",
                "message": _("{0} ingreso(s) requieren conciliación.").format(
                    unreconciled_count
                ),
                "route": ["List", "CC Funding Source"],
            }
        )

    result["alerts"] = alerts


@frappe.whitelist()
def get_executive_dashboard(project: str | None = None) -> dict[str, Any]:
    """Return the canonical dashboard while keeping the alert strip compact."""
    if not callable(get_reporting_summary):
        raise RuntimeError("Canonical BI01 reporting service is unavailable.")
    result = _implementation.get_executive_dashboard(project)
    _append_missing_actionable_alerts(result)
    alerts = list(result.get("alerts") or [])
    result["alerts"] = alerts[:4]
    return result


def __getattr__(name: str) -> Any:
    return getattr(_implementation, name)


__all__ = ["get_executive_dashboard"]
