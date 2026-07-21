from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

from erpnext.construcontrol.access import (
	accessible_project_profiles,
	assert_project_access,
	require_construcontrol_access,
	resolve_accessible_project,
)
from erpnext.construcontrol.business_rules import expense_amounts


def _active_filters(project: str | None = None) -> dict[str, Any]:
	filters: dict[str, Any] = {"is_logically_deleted": 0}
	if project:
		filters["project"] = project
	return filters


def _safe_percent(value: float, total: float) -> float:
	return round((flt(value) / flt(total)) * 100, 2) if flt(total) else 0.0


def _contract_value(row: Any) -> float:
	return flt(row.get("project_value_hnl") or row.get("labor_value_hnl"))


def _financial_control(
	phases: list[Any],
	expenses: list[Any],
	contracts: list[Any],
) -> dict[str, Any]:
	"""Return non-duplicated approved costs and commitments by phase and project."""
	phase_actual: dict[str, float] = defaultdict(float)
	phase_commitments: dict[str, float] = defaultdict(float)
	unphased_actual = 0.0
	unphased_commitments = 0.0

	active_contracts: set[str] = set()
	for row in contracts:
		if str(row.get("status") or "").lower() == "cancelled":
			continue
		name = str(row.get("name") or "")
		if name:
			active_contracts.add(name)
		value = _contract_value(row)
		phase = str(row.get("phase") or "")
		if phase:
			phase_commitments[phase] += value
		else:
			unphased_commitments += value

	for row in expenses:
		recognized, _paid, _pending = expense_amounts(
			row.get("amount_hnl"),
			row.get("payment_status"),
			row.get("financial_status"),
			row.get("paid_amount_hnl"),
			row.get("balance_due_hnl"),
			row.get("professional_approval_status"),
		)
		phase = str(row.get("phase") or "")
		contract = str(row.get("labor_contract") or "")
		if phase:
			phase_actual[phase] += recognized
			if not contract or contract not in active_contracts:
				phase_commitments[phase] += recognized
		else:
			unphased_actual += recognized
			if not contract or contract not in active_contracts:
				unphased_commitments += recognized

	phase_names = {str(row.get("name") or "") for row in phases}
	orphan_actual = sum(value for phase, value in phase_actual.items() if phase not in phase_names)
	orphan_commitments = sum(value for phase, value in phase_commitments.items() if phase not in phase_names)
	return {
		"phase_actual": phase_actual,
		"phase_commitments": phase_commitments,
		"unphased_actual": round(unphased_actual + orphan_actual, 2),
		"unphased_commitments": round(unphased_commitments + orphan_commitments, 2),
	}


def _calculate_project_control(project: str, *, persist: bool) -> dict[str, Any]:
	project = assert_project_access(project, write=persist)

	profile_name = frappe.db.get_value(
		"CC Project Profile",
		{"project": project, "is_logically_deleted": 0},
		"name",
	)
	if not profile_name:
		frappe.throw(_("El proyecto todavía no tiene un perfil ConstruControl."))

	phases = frappe.get_all(
		"CC Construction Phase",
		filters=_active_filters(project),
		fields=[
			"name",
			"phase_name",
			"budget_hnl",
			"progress_percent",
			"target_end_date",
			"status",
			"milestone_date",
		],
	)
	expenses = frappe.get_all(
		"CC Expense Control",
		filters=_active_filters(project),
		fields=[
			"phase",
			"labor_contract",
			"amount_hnl",
			"paid_amount_hnl",
			"balance_due_hnl",
			"payment_status",
			"financial_status",
			"professional_approval_status",
		],
	)
	contracts = frappe.get_all(
		"CC Labor Contract",
		filters=_active_filters(project),
		fields=[
			"name",
			"phase",
			"project_value_hnl",
			"labor_value_hnl",
			"paid_hnl",
			"balance_hnl",
			"status",
		],
	)

	financial = _financial_control(phases, expenses, contracts)
	phase_actual = financial["phase_actual"]
	phase_commitments = financial["phase_commitments"]

	today_date = getdate(today())
	weighted_progress_numerator = 0.0
	weighted_progress_denominator = 0.0
	total_budget = 0.0
	total_actual = flt(financial["unphased_actual"])
	total_committed = flt(financial["unphased_commitments"])
	delayed = 0
	at_risk = 0

	phase_rows: list[dict[str, Any]] = []
	for row in phases:
		phase_name = str(row.get("name") or "")
		budget = flt(row.get("budget_hnl"))
		actual = flt(phase_actual.get(phase_name, 0.0))
		committed = flt(phase_commitments.get(phase_name, 0.0))
		available = budget - committed
		progress = flt(row.get("progress_percent"))
		end_date = getdate(row.get("target_end_date")) if row.get("target_end_date") else None
		status = (
			"completed"
			if progress >= 100 or str(row.get("status") or "").lower() == "completed"
			else "on_track"
		)
		if status != "completed" and end_date and end_date < today_date:
			status = "delayed"
			delayed += 1
		elif status != "completed" and (
			available < 0 or (end_date and (end_date - today_date).days <= 7 and progress < 80)
		):
			status = "at_risk"
			at_risk += 1
		elif progress <= 0:
			status = "not_started"

		if persist:
			frappe.db.set_value(
				"CC Construction Phase",
				phase_name,
				{
					"committed_hnl": committed,
					"actual_cost_hnl": actual,
					"available_budget_hnl": available,
					"financial_progress_percent": _safe_percent(actual, budget),
					"schedule_status": status,
				},
				update_modified=False,
			)

		weight = budget if budget > 0 else 1.0
		weighted_progress_numerator += progress * weight
		weighted_progress_denominator += weight
		total_budget += budget
		total_actual += actual
		total_committed += committed
		phase_rows.append(
			{
				"name": phase_name,
				"phase_name": row.get("phase_name") or phase_name,
				"budget_hnl": round(budget, 2),
				"actual_cost_hnl": round(actual, 2),
				"committed_hnl": round(committed, 2),
				"available_budget_hnl": round(available, 2),
				"physical_progress_percent": round(progress, 2),
				"financial_progress_percent": _safe_percent(actual, budget),
				"schedule_status": status,
				"target_end_date": row.get("target_end_date"),
				"milestone_date": row.get("milestone_date"),
			}
		)

	profile = frappe.get_doc("CC Project Profile", profile_name)
	original_budget = flt(profile.get("original_budget_hnl"))
	updated_budget = flt(profile.get("updated_budget_hnl")) or total_budget or original_budget
	physical = (
		round(weighted_progress_numerator / weighted_progress_denominator, 2)
		if weighted_progress_denominator
		else 0.0
	)
	financial_progress = _safe_percent(total_actual, updated_budget)
	variance = updated_budget - total_committed
	alert = "critical" if delayed or variance < 0 else "attention" if at_risk else "normal"
	schedule = (
		"delayed"
		if delayed
		else "at_risk"
		if at_risk
		else "completed"
		if phases and physical >= 100
		else "on_track"
	)

	values = {
		"updated_budget_hnl": updated_budget,
		"committed_hnl": total_committed,
		"actual_cost_hnl": total_actual,
		"available_budget_hnl": updated_budget - total_committed,
		"physical_progress_percent": physical,
		"financial_progress_percent": financial_progress,
		"budget_variance_hnl": variance,
		"schedule_status": schedule,
		"alert_level": alert,
	}
	if persist:
		changed = False
		for fieldname, value in values.items():
			if not profile.meta.has_field(fieldname):
				continue
			current = profile.get(fieldname)
			differs = flt(current) != flt(value) if isinstance(value, int | float) else current != value
			if differs:
				profile.set(fieldname, value)
				changed = True
		if changed:
			profile.flags.ignore_construcontrol_audit = True
			profile.save(ignore_permissions=True)

	return {
		"project": project,
		"profile": profile.name,
		"project_name": profile.get("project_name") or project,
		"original_budget_hnl": round(original_budget, 2),
		"updated_budget_hnl": round(updated_budget, 2),
		"committed_hnl": round(total_committed, 2),
		"actual_cost_hnl": round(total_actual, 2),
		"available_budget_hnl": round(updated_budget - total_committed, 2),
		"physical_progress_percent": physical,
		"financial_progress_percent": financial_progress,
		"budget_variance_hnl": round(variance, 2),
		"schedule_status": schedule,
		"alert_level": alert,
		"phase_count": len(phases),
		"delayed_phase_count": delayed,
		"at_risk_phase_count": at_risk,
		"unphased_actual_hnl": round(flt(financial["unphased_actual"]), 2),
		"unphased_committed_hnl": round(flt(financial["unphased_commitments"]), 2),
		"phases": phase_rows,
	}


@frappe.whitelist(methods=["POST"])
def recalculate_project_control(project: str) -> dict[str, Any]:
	"""Persist calculated project indicators after an explicit authorized action."""
	require_construcontrol_access(write=True)
	return _calculate_project_control(project, persist=True)


@frappe.whitelist()
def get_project_center(project: str | None = None) -> dict[str, Any]:
	"""Return project indicators without writing or producing audit noise."""
	require_construcontrol_access()
	project = resolve_accessible_project(project)
	projects = accessible_project_profiles()
	if not project:
		return {"project": None, "projects": projects, "phases": []}

	summary = _calculate_project_control(project, persist=False)
	summary["projects"] = projects
	summary["contracts"] = frappe.get_all(
		"CC Labor Contract",
		filters=_active_filters(project),
		fields=[
			"name",
			"contract_code",
			"contractor_name",
			"status",
			"project_value_hnl",
			"paid_hnl",
			"balance_hnl",
		],
		order_by="modified desc",
		limit_page_length=10,
	)
	summary["materials"] = frappe.get_all(
		"CC Material Ledger",
		filters=_active_filters(project),
		fields=["name", "material_name", "current_qty", "unit", "stock_status", "low_stock_threshold"],
		order_by="stock_status asc, material_name asc",
		limit_page_length=12,
	)
	summary["recent_progress"] = frappe.get_all(
		"CC Progress Update",
		filters=_active_filters(project),
		fields=["name", "posting_date", "title", "phase", "progress_percent", "quality", "responsible"],
		order_by="posting_date desc, creation desc",
		limit_page_length=10,
	)
	return summary


__all__ = ["get_project_center", "recalculate_project_control"]
