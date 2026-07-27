from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.dashboard.analytics_core import number
from nexora.dashboard.contract_query import contract_totals
from nexora.dashboard.executive import get_executive_snapshot as canonical_snapshot
from nexora.dashboard.expense_query import expense_breakdowns, expense_page
from nexora.dashboard.pending_query import pending_commitments
from nexora.permissions import require_action

SOURCE_TOTAL_FIELDS = (
	"opening_funds_hnl",
	"opening_reserved_hnl",
	"closing_funds_hnl",
	"closing_reserved_hnl",
	"current_funds_hnl",
	"current_reserved_hnl",
	"received_hnl",
	"spent_hnl",
	"transfer_in_hnl",
	"transfer_out_hnl",
	"returned_hnl",
	"reversed_hnl",
	"reserved_hnl",
	"released_hnl",
)
DIMENSION_FILTERS = ("source", "entity", "economic_category", "cost_center")


def _payload(value: str | Mapping[str, Any]) -> dict[str, Any]:
	data = dict(value) if isinstance(value, Mapping) else frappe.parse_json(value)
	if not isinstance(data, dict):
		frappe.throw(_("El payload del resumen debe ser un objeto JSON."))
	return data


def _text(data: Mapping[str, Any], fieldname: str) -> str | None:
	value = str(data.get(fieldname) or "").strip()
	return value or None


def _source_totals(rows: list[Mapping[str, Any]]) -> dict[str, float]:
	totals = {
		fieldname: number(sum(float(row.get(fieldname) or 0) for row in rows))
		for fieldname in SOURCE_TOTAL_FIELDS
	}
	for prefix in ("opening", "closing", "current"):
		totals[f"{prefix}_available_hnl"] = number(
			totals[f"{prefix}_funds_hnl"] - totals[f"{prefix}_reserved_hnl"]
		)
	return totals


def _income_channels(rows: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
	channels: dict[str, float] = {}
	for row in rows:
		channel = str(row.get("channel") or "Other")
		channels[channel] = channels.get(channel, 0) + float(row.get("received_hnl") or 0)
	return [
		{"label": label, "amount_hnl": number(amount)}
		for label, amount in sorted(channels.items(), key=lambda item: item[1], reverse=True)
	]


@frappe.whitelist(methods=["POST"])
def get_executive_snapshot(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Align executive KPIs, charts and detail rows with the selected report filters."""
	require_action("view_reports")
	data = _payload(payload)
	snapshot = canonical_snapshot(data)
	analytics = snapshot.setdefault("analytics", {})
	executive = snapshot.setdefault("executive", {})

	expenses = expense_page({**data, "page": 1, "page_size": 8})
	analytics["expense_rows"] = expenses["rows"]
	analytics["expense_pagination"] = expenses["pagination"]
	analytics.update(expense_breakdowns(data))
	executive["spent_hnl"] = expenses["summary"]["amount_hnl"]

	contracts = contract_totals(data)
	analytics["contract_totals"] = contracts
	analytics["contract_count"] = contracts["contract_count"]
	executive["paid_hnl"] = contracts["paid_hnl"]

	source = _text(data, "source")
	if source:
		source_rows = list(analytics.get("rows") or [])
		totals = _source_totals(source_rows)
		analytics["source_totals"] = totals
		analytics["income_by_channel"] = _income_channels(source_rows)
		analytics["unreconciled_count"] = sum(
			1 for row in source_rows if row.get("reconciliation_status") != "Reconciled"
		)
		executive.update(
			{
				"received_hnl": totals["received_hnl"],
				"cash_available_hnl": totals["closing_available_hnl"],
				"committed_hnl": totals["closing_reserved_hnl"],
				"projected_available_hnl": totals["closing_available_hnl"],
			}
		)

	active_dimensions = [fieldname for fieldname in DIMENSION_FILTERS if _text(data, fieldname)]
	if active_dimensions:
		pending = pending_commitments({**data, "page": 1, "page_size": 8})
		snapshot["pending_accounts"] = pending
		executive["pending_obligations_hnl"] = pending["total_hnl"]

	snapshot["filter_context"] = {
		"active": {
			fieldname: _text(data, fieldname)
			for fieldname in (
				"project",
				"source",
				"economic_category",
				"cost_center",
				"entity",
				"payment_method",
				"contractor",
				"contract_status",
			)
			if _text(data, fieldname)
		},
		"expense_kpis_filtered": True,
		"source_kpis_filtered": bool(source),
		"contract_kpis_filtered": True,
		"pending_kpis_filtered": bool(active_dimensions),
	}
	return snapshot
