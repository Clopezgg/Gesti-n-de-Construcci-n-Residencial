from __future__ import annotations

from typing import Any

import frappe

from erpnext.construcontrol import executive_impl as _implementation

# Explicit BI01 contract fields kept on the public service surface.
EXECUTIVE_CONTRACT_FIELDS = (
    "expense_total_hnl",
    "paid_hnl",
    "cash_available_hnl",
    "schedule_status_label",
    "action_label",
    "record_type_label",
    "recent_activity",
)


@frappe.whitelist()
def get_executive_dashboard(project: str | None = None) -> dict[str, Any]:
    """Return the canonical dashboard while keeping the alert strip compact."""
    result = _implementation.get_executive_dashboard(project)
    alerts = list(result.get("alerts") or [])
    result["alerts"] = alerts[:4]
    return result


def __getattr__(name: str) -> Any:
    return getattr(_implementation, name)


__all__ = ["get_executive_dashboard"]
