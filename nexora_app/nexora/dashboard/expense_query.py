from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.dashboard.analytics_core import normalize_period, number
from nexora.permissions import require_action, require_project_access

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


def _payload(value: str | Mapping[str, Any]) -> dict[str, Any]:
	data = dict(value) if isinstance(value, Mapping) else frappe.parse_json(value)
	if not isinstance(data, dict):
		frappe.throw(_("El payload de gastos debe ser un objeto JSON."))
	return data


def _text(data: Mapping[str, Any], fieldname: str) -> str | None:
	value = str(data.get(fieldname) or "").strip()
	return value or None


def _period(data: Mapping[str, Any]) -> tuple[str, str]:
	try:
		return normalize_period(data.get("from_date"), data.get("to_date"))
	except (TypeError, ValueError) as exc:
		frappe.throw(_(str(exc)))
		raise AssertionError from exc


def _query_parts(data: Mapping[str, Any]) -> tuple[str, str, dict[str, Any]]:
	project = _text(data, "project")
	require_project_access(project, action="view_financial_details")
	start, end = _period(data)
	operation_conditions = [
		"o.status='Executed'",
		"o.operation_type IN ('Outflow','Commitment Execution')",
		"o.operation_date BETWEEN %(start)s AND %(end)s",
	]
	effect_conditions = [
		"fx.dimension='Funds'",
		"fx.amount_hnl<0",
		"COALESCE(fx.is_reversal,0)=0",
	]
	params: dict[str, Any] = {"start": start, "end": end}
	for fieldname, column in (
		("project", "o.project"),
		("entity", "o.beneficiary"),
		("payment_method", "o.payment_method"),
	):
		value = project if fieldname == "project" else _text(data, fieldname)
		if value:
			operation_conditions.append(f"{column}=%({fieldname})s")
			params[fieldname] = value
	cost_center = _text(data, "cost_center")
	if cost_center:
		effect_conditions.append("COALESCE(fx.cost_center,o.cost_center)=%(cost_center)s")
		params["cost_center"] = cost_center
	economic_category = _text(data, "economic_category")
	if economic_category:
		effect_conditions.append(
			"COALESCE(fx.economic_category,o.economic_category)=%(economic_category)s"
		)
		params["economic_category"] = economic_category
	source = _text(data, "source")
	if source:
		effect_conditions.append("fx.fund_source=%(source)s")
		params["source"] = source
	return " AND ".join(operation_conditions), " AND ".join(effect_conditions), params


def expense_page(data: Mapping[str, Any]) -> dict[str, Any]:
	where, effect_where, params = _query_parts(data)
	page = max(int(data.get("page") or 1), 1)
	page_size = min(max(int(data.get("page_size") or DEFAULT_PAGE_SIZE), 1), MAX_PAGE_SIZE)
	params.update({"limit": page_size, "offset": (page - 1) * page_size})
	join = f"INNER JOIN `tabNXR Operation Effect` fx ON fx.operation=o.name AND {effect_where}"
	rows = frappe.db.sql(
		f"""
		SELECT o.name,o.document_number,o.operation_date,o.operation_code,o.operation_type,o.project,
			GROUP_CONCAT(DISTINCT COALESCE(fx.cost_center,o.cost_center)
				ORDER BY COALESCE(fx.cost_center,o.cost_center) SEPARATOR ', ') cost_center,
			GROUP_CONCAT(DISTINCT COALESCE(fx.economic_category,o.economic_category)
				ORDER BY COALESCE(fx.economic_category,o.economic_category) SEPARATOR ', ') economic_category,
			o.beneficiary_doctype,o.beneficiary,
			COALESCE(entity.display_name,o.beneficiary,'Sin beneficiario') beneficiary_label,
			o.payment_method,o.external_reference,
			COALESCE(SUM(-fx.amount_hnl),0) amount_hnl,o.status,
			GROUP_CONCAT(DISTINCT fx.fund_source ORDER BY fx.fund_source SEPARATOR ', ') sources
		FROM `tabNXR Operation` o
		{join}
		LEFT JOIN `tabNXR Entity` entity
			ON entity.name=o.beneficiary AND o.beneficiary_doctype='NXR Entity'
		WHERE {where}
		GROUP BY o.name
		ORDER BY o.operation_date DESC,o.creation DESC
		LIMIT %(limit)s OFFSET %(offset)s
		""",
		params,
		as_dict=True,
	)
	totals = frappe.db.sql(
		f"""
		SELECT COUNT(DISTINCT o.name) operation_count,COALESCE(SUM(-fx.amount_hnl),0) amount_hnl
		FROM `tabNXR Operation` o {join}
		WHERE {where}
		""",
		params,
		as_dict=True,
	)[0]
	start, end = _period(data)
	return {
		"rows": [{**dict(row), "amount_hnl": number(row.amount_hnl)} for row in rows],
		"pagination": {
			"page": page,
			"page_size": page_size,
			"total": int(totals.operation_count or 0),
		},
		"summary": {"amount_hnl": number(totals.amount_hnl)},
		"period": {"from_date": start, "to_date": end},
	}


@frappe.whitelist(methods=["POST"])
def get_expense_page(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Return FI02 rows whose amount matches the selected source and dimensions."""
	require_action("view_financial_details")
	return expense_page(_payload(payload))
