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


def _query_params(data: Mapping[str, Any]) -> dict[str, Any]:
	project = _text(data, "project")
	require_project_access(project, action="view_financial_details")
	start, end = _period(data)
	return {
		"start": start,
		"end": end,
		"project": project,
		"entity": _text(data, "entity"),
		"payment_method": _text(data, "payment_method"),
		"cost_center": _text(data, "cost_center"),
		"economic_category": _text(data, "economic_category"),
		"source": _text(data, "source"),
	}


_EFFECT_JOIN = """
INNER JOIN `tabNXR Operation Effect` fx
	ON fx.operation=o.name
	AND fx.dimension='Funds'
	AND fx.amount_hnl<0
	AND COALESCE(fx.is_reversal,0)=0
	AND (%(cost_center)s IS NULL OR COALESCE(fx.cost_center,o.cost_center)=%(cost_center)s)
	AND (
		%(economic_category)s IS NULL
		OR COALESCE(fx.economic_category,o.economic_category)=%(economic_category)s
	)
	AND (%(source)s IS NULL OR fx.fund_source=%(source)s)
"""

_OPERATION_WHERE = """
o.status='Executed'
	AND o.operation_type IN ('Outflow','Commitment Execution')
	AND o.operation_date BETWEEN %(start)s AND %(end)s
	AND (%(project)s IS NULL OR o.project=%(project)s)
	AND (%(entity)s IS NULL OR o.beneficiary=%(entity)s)
	AND (%(payment_method)s IS NULL OR o.payment_method=%(payment_method)s)
"""


def expense_breakdowns(data: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
	"""Aggregate FI02 charts with the exact same filters used by its detail rows."""
	params = _query_params(data)
	categories = frappe.db.sql(
		"""
		SELECT COALESCE(fx.economic_category,o.economic_category,'Sin clasificar') code,
			COALESCE(ec.category_name,fx.economic_category,o.economic_category,'Sin clasificar') label,
			COALESCE(SUM(-fx.amount_hnl),0) amount_hnl,
			COUNT(DISTINCT o.name) operation_count
		FROM `tabNXR Operation` o
		"""
		+ _EFFECT_JOIN
		+ """
		LEFT JOIN `tabNXR Economic Category` ec
			ON ec.name=COALESCE(fx.economic_category,o.economic_category)
		WHERE """
		+ _OPERATION_WHERE
		+ """
		GROUP BY COALESCE(fx.economic_category,o.economic_category),ec.category_name
		ORDER BY amount_hnl DESC
		LIMIT 20
		""",
		params,
		as_dict=True,
	)
	providers = frappe.db.sql(
		"""
		SELECT COALESCE(entity.display_name,o.beneficiary,'Sin beneficiario') label,
			COALESCE(SUM(-fx.amount_hnl),0) amount_hnl,
			COUNT(DISTINCT o.name) operation_count
		FROM `tabNXR Operation` o
		"""
		+ _EFFECT_JOIN
		+ """
		LEFT JOIN `tabNXR Entity` entity
			ON entity.name=o.beneficiary AND o.beneficiary_doctype='NXR Entity'
		WHERE """
		+ _OPERATION_WHERE
		+ """
		GROUP BY o.beneficiary,entity.display_name
		ORDER BY amount_hnl DESC
		LIMIT 10
		""",
		params,
		as_dict=True,
	)
	return {
		"expenses_by_category": [
			{
				"code": row.code,
				"label": row.label,
				"amount_hnl": number(row.amount_hnl),
				"operation_count": int(row.operation_count),
			}
			for row in categories
		],
		"providers": [
			{
				"label": row.label,
				"amount_hnl": number(row.amount_hnl),
				"operation_count": int(row.operation_count),
			}
			for row in providers
		],
	}


def expense_page(data: Mapping[str, Any]) -> dict[str, Any]:
	params = _query_params(data)
	page = max(int(data.get("page") or 1), 1)
	page_size = min(max(int(data.get("page_size") or DEFAULT_PAGE_SIZE), 1), MAX_PAGE_SIZE)
	params.update({"limit": page_size, "offset": (page - 1) * page_size})
	rows = frappe.db.sql(
		"""
		SELECT o.name,o.document_number,o.operation_date,o.operation_code,o.operation_type,o.project,
			GROUP_CONCAT(DISTINCT COALESCE(fx.cost_center,o.cost_center)
				ORDER BY COALESCE(fx.cost_center,o.cost_center) SEPARATOR ', ') cost_center,
			GROUP_CONCAT(DISTINCT COALESCE(fx.economic_category,o.economic_category)
				ORDER BY COALESCE(fx.economic_category,o.economic_category) SEPARATOR ', ')
				economic_category,
			o.beneficiary_doctype,o.beneficiary,
			COALESCE(entity.display_name,o.beneficiary,'Sin beneficiario') beneficiary_label,
			o.payment_method,o.external_reference,
			COALESCE(SUM(-fx.amount_hnl),0) amount_hnl,o.status,
			GROUP_CONCAT(DISTINCT fx.fund_source ORDER BY fx.fund_source SEPARATOR ', ') sources
		FROM `tabNXR Operation` o
		"""
		+ _EFFECT_JOIN
		+ """
		LEFT JOIN `tabNXR Entity` entity
			ON entity.name=o.beneficiary AND o.beneficiary_doctype='NXR Entity'
		WHERE """
		+ _OPERATION_WHERE
		+ """
		GROUP BY o.name
		ORDER BY o.operation_date DESC,o.creation DESC
		LIMIT %(limit)s OFFSET %(offset)s
		""",
		params,
		as_dict=True,
	)
	totals = frappe.db.sql(
		"""
		SELECT COUNT(DISTINCT o.name) operation_count,
			COALESCE(SUM(-fx.amount_hnl),0) amount_hnl
		FROM `tabNXR Operation` o
		"""
		+ _EFFECT_JOIN
		+ " WHERE "
		+ _OPERATION_WHERE,
		params,
		as_dict=True,
	)[0]
	return {
		"rows": [{**dict(row), "amount_hnl": number(row.amount_hnl)} for row in rows],
		"pagination": {
			"page": page,
			"page_size": page_size,
			"total": int(totals.operation_count or 0),
		},
		"summary": {"amount_hnl": number(totals.amount_hnl)},
		"period": {"from_date": params["start"], "to_date": params["end"]},
	}


@frappe.whitelist(methods=["POST"])
def get_expense_page(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Return FI02 rows whose amount matches the selected source and dimensions."""
	require_action("view_financial_details")
	return expense_page(_payload(payload))
