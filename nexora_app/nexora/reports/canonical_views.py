from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe

from nexora.dashboard.snapshot_query import get_executive_snapshot
from nexora.permissions import require_action, require_project_access
from nexora.reports.service import _data


@frappe.whitelist(methods=["POST"])
def get_financial_report(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Return the filtered executive dataset used by BI01 and the report center."""
	data = _data(payload)
	require_action("view_reports")
	require_project_access(str(data.get("project") or "").strip() or None, action="view_reports")
	return get_executive_snapshot(data)


@frappe.whitelist(methods=["POST"])
def get_cost_report(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Return FI02 totals and categories from the canonical filtered snapshot."""
	data = _data(payload)
	require_action("view_financial_details")
	require_project_access(
		str(data.get("project") or "").strip() or None,
		action="view_financial_details",
	)
	snapshot = get_executive_snapshot(data)
	categories = snapshot.get("analytics", {}).get("expenses_by_category", [])
	return {
		"categories": {str(row.get("label")): row.get("amount_hnl", 0) for row in categories},
		"total": snapshot.get("executive", {}).get("spent_hnl", 0),
		"filter_context": snapshot.get("filter_context", {}),
	}


@frappe.whitelist(methods=["POST"])
def reconcile_totals(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Reconcile filtered source totals without bypassing project permissions."""
	data = _data(payload)
	require_action("view_financial_details")
	project = str(data.get("project") or "").strip() or None
	require_project_access(project, action="view_financial_details")
	snapshot = get_executive_snapshot(data)
	totals = snapshot.get("analytics", {}).get("source_totals", {})
	return {
		"inflows": totals.get("received_hnl", 0),
		"outflows": snapshot.get("executive", {}).get("spent_hnl", 0),
		"net": totals.get("closing_available_hnl", 0),
		"operation_count": int(
			snapshot.get("analytics", {}).get("expense_pagination", {}).get("total") or 0
		),
		"filter_context": snapshot.get("filter_context", {}),
	}
