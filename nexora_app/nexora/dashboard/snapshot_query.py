from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.close.as_of import budget_snapshot_as_of
from nexora.dashboard.analytics_core import normalize_period, number
from nexora.dashboard.contract_query import contract_totals
from nexora.dashboard.executive import (
	_contract_page,
	_critical_inventory,
	_income_by_channel,
	_source_statement,
	_source_totals,
)
from nexora.dashboard.expense_query import expense_breakdowns, expense_page
from nexora.dashboard.operational_query import build_operational_sections
from nexora.dashboard.pending_query import pending_commitments
from nexora.permissions import require_action, require_project_access

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


def _period(data: Mapping[str, Any]) -> tuple[str, str]:
	try:
		return normalize_period(data.get("from_date"), data.get("to_date") or frappe.utils.today())
	except (TypeError, ValueError) as exc:
		frappe.throw(_(str(exc)))
		raise AssertionError from exc


def _filtered_source_totals(rows: list[Mapping[str, Any]]) -> dict[str, float]:
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


def _unreconciled_count(
	project: str | None,
	period_end: str,
	source_rows: list[Mapping[str, Any]] | None,
) -> int:
	if source_rows is not None:
		return sum(
			1 for row in source_rows if row.get("reconciliation_status") != "Reconciled"
		)
	filters: dict[str, Any] = {
		"status": ["not in", ["Draft", "Cancelled"]],
		"source_date": ["<=", period_end],
		"reconciliation_status": ["!=", "Reconciled"],
	}
	if project:
		filters["project"] = project
	return int(frappe.db.count("NXR Fund Source", filters=filters))


def _historical_budgets(data: Mapping[str, Any], project: str | None, end: str) -> dict[str, Any]:
	result = budget_snapshot_as_of(
		project,
		end,
		economic_category=_text(data, "economic_category"),
		cost_center=_text(data, "cost_center"),
	)
	return {
		"active_budget_count": result["budget_count"],
		"total_approved_hnl": result["total_approved_hnl"],
		"total_committed_hnl": result["total_committed_hnl"],
		"total_executed_hnl": result["total_executed_hnl"],
		"total_available_hnl": result["total_available_hnl"],
		"utilization_percent": result["utilization_percent"],
		"lines": result["lines"],
		"basis": result["basis"],
		"filter_context": result["filter_context"],
	}


def _finance_summary(
	source_totals: Mapping[str, Any],
	source_rows: list[dict[str, Any]],
	source_count: int,
) -> dict[str, Any]:
	opening_funds = number(source_totals.get("opening_funds_hnl"))
	closing_funds = number(source_totals.get("closing_funds_hnl"))
	inflows = number(
		float(source_totals.get("received_hnl") or 0)
		+ float(source_totals.get("returned_hnl") or 0)
	)
	outflows = number(source_totals.get("spent_hnl"))
	return {
		"source_count": int(source_count),
		"total_balance_hnl": closing_funds,
		"total_reserved_hnl": number(source_totals.get("closing_reserved_hnl")),
		"total_available_hnl": number(source_totals.get("closing_available_hnl")),
		"inflows_hnl": inflows,
		"outflows_hnl": outflows,
		"net_flow_hnl": number(closing_funds - opening_funds),
		"sources": source_rows,
		"basis": "Saldos del Libro Central a la fecha final; las fuentes visibles están limitadas y el total es server-side.",
	}


@frappe.whitelist(methods=["POST"])
def get_executive_snapshot(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Build the filtered dashboard and reports response with bounded queries."""
	require_action("view_reports")
	data = _payload(payload)
	project = _text(data, "project")
	require_project_access(project, action="view_reports")
	start, end = _period(data)
	query_data = {**data, "from_date": start, "to_date": end}
	period_is_filtered = bool(data.get("from_date") or data.get("to_date"))

	source_page = _source_statement({**query_data, "page": 1, "page_size": 8})
	expenses = expense_page({**query_data, "page": 1, "page_size": 8})
	contracts_page = _contract_page({**query_data, "page": 1, "page_size": 8})
	contracts = contract_totals(query_data)
	source = _text(data, "source")
	source_rows = list(source_page["rows"])
	if source:
		source_totals = _filtered_source_totals(source_rows)
		income_channels = _income_channels(source_rows)
		unreconciled = _unreconciled_count(project, end, source_rows)
	else:
		source_totals = _source_totals(project, start, end)
		income_channels = _income_by_channel(project, start, end)
		unreconciled = _unreconciled_count(project, end, None)

	active_dimensions = [fieldname for fieldname in DIMENSION_FILTERS if _text(data, fieldname)]
	pending = pending_commitments({**query_data, "page": 1, "page_size": 8})
	budgets = _historical_budgets(query_data, project, end)
	finance = _finance_summary(
		source_totals,
		source_rows,
		int(source_page.get("pagination", {}).get("total") or 0),
	)
	contract_rows = [dict(row) for row in contracts_page["rows"]]
	snapshot = build_operational_sections(
		project=project,
		period_start=start,
		period_end=end,
		finance=finance,
		budgets=budgets,
		pending=pending,
		contract_rows=contract_rows,
		contract_count=int(contracts.get("contract_count") or 0),
	)

	breakdowns = expense_breakdowns(query_data)
	snapshot["analytics"] = {
		"rows": source_rows,
		"expense_rows": expenses["rows"],
		"contracts": contract_rows,
		"source_pagination": source_page["pagination"],
		"expense_pagination": expenses["pagination"],
		"contract_pagination": contracts_page["pagination"],
		"source_totals": source_totals,
		"contract_totals": contracts,
		"contract_count": contracts["contract_count"],
		"income_by_channel": income_channels,
		"critical_inventory": _critical_inventory(project),
		"unreconciled_count": unreconciled,
		**breakdowns,
	}
	snapshot["executive"] = {
		"received_hnl": source_totals["received_hnl"],
		"spent_hnl": expenses["summary"]["amount_hnl"],
		"paid_hnl": contracts["paid_hnl"],
		"cash_available_hnl": source_totals["closing_available_hnl"],
		"committed_hnl": source_totals["closing_reserved_hnl"],
		"budget_available_hnl": number(budgets.get("total_available_hnl")),
		"projected_available_hnl": source_totals["closing_available_hnl"],
		"pending_obligations_hnl": number(pending.get("total_hnl")),
		"projection_basis": (
			"El disponible al cierre ya descuenta reservas; las obligaciones pendientes "
			"se muestran por separado para evitar doble conteo."
		),
		"financial_percent": number(budgets.get("utilization_percent")),
	}
	snapshot["period"] = {"from_date": start, "to_date": end}
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
		"pending_kpis_filtered": period_is_filtered or bool(active_dimensions),
		"budget_kpis_filtered": period_is_filtered
		or bool(_text(data, "economic_category") or _text(data, "cost_center")),
		"bounded_operational_queries": True,
	}
	return snapshot
