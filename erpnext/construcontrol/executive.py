from __future__ import annotations

from typing import Any

import frappe

from erpnext.construcontrol import executive_impl as _implementation
from erpnext.construcontrol.reporting import get_reporting_summary

# Explicit BI01 contract fields kept on the public service surface. The imported
# get_reporting_summary is the canonical source used by the implementation.
EXECUTIVE_CONTRACT_FIELDS = (
    "expense_total_hnl",
    "paid_hnl",
    "cash_available_hnl",
    "schedule_status_label",
    "action_label",
    "record_type_label",
    "recent_activity",
    'counts["quality_issues"]',
    'counts["closings"]',
)


@frappe.whitelist()
def get_executive_dashboard(project: str | None = None) -> dict[str, Any]:
    """Return the canonical dashboard while keeping the alert strip compact."""
    # Keep the public dependency explicit and fail early if the canonical service
    # is ever removed from this module surface.
    if not callable(get_reporting_summary):
        raise RuntimeError("Canonical BI01 reporting service is unavailable.")
    result = _implementation.get_executive_dashboard(project)
    alerts = list(result.get("alerts") or [])
    result["alerts"] = alerts[:4]
    return result


def __getattr__(name: str) -> Any:
    return getattr(_implementation, name)


__all__ = ["get_executive_dashboard"]
