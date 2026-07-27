from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.dashboard.analytics_core import normalize_period, number
from nexora.permissions import require_project_access


def _text(data: Mapping[str, Any], fieldname: str) -> str | None:
	value = str(data.get(fieldname) or "").strip()
	return value or None


def contract_totals(data: Mapping[str, Any]) -> dict[str, Any]:
	"""Aggregate CO01 with the same project, contractor, status and period filters."""
	project = _text(data, "project")
	require_project_access(project, action="view_reports")
	try:
		start, end = normalize_period(data.get("from_date"), data.get("to_date"))
	except (TypeError, ValueError) as exc:
		frappe.throw(_(str(exc)))
		raise AssertionError from exc
	params: dict[str, Any] = {"start": start, "end": end}
	for fieldname, _column, value in (
		("project", "c.project", project),
		("contract", "c.name", _text(data, "contract")),
		("contractor", "c.contractor", _text(data, "contractor")),
		("contract_status", "c.status", _text(data, "contract_status")),
	):
		params[fieldname] = value
	row = frappe.db.sql(
		"""
		SELECT COUNT(*) contract_count,
			COALESCE(SUM(c.current_amount*COALESCE(c.exchange_rate,1)),0) contract_value_hnl,
			COALESCE(SUM(c.executed_amount*COALESCE(c.exchange_rate,1)),0) executed_hnl,
			COALESCE(SUM(c.paid_amount*COALESCE(c.exchange_rate,1)),0) paid_hnl,
			COALESCE(SUM(c.pending_amount*COALESCE(c.exchange_rate,1)),0) balance_hnl,
			COALESCE(SUM(c.retention_balance*COALESCE(c.exchange_rate,1)),0)
				retention_balance_hnl
		FROM `tabNXR Contract` c
		WHERE c.status!='Cancelled Before Active'
			AND c.start_date<=%(end)s
			AND (c.current_end_date IS NULL OR c.current_end_date>=%(start)s)
			AND (%(project)s IS NULL OR c.project=%(project)s)
			AND (%(contract)s IS NULL OR c.name=%(contract)s)
			AND (%(contractor)s IS NULL OR c.contractor=%(contractor)s)
			AND (%(contract_status)s IS NULL OR c.status=%(contract_status)s)
		""",
		params,
		as_dict=True,
	)[0]
	return {
		"contract_count": int(row.contract_count or 0),
		"contract_value_hnl": number(row.contract_value_hnl),
		"executed_hnl": number(row.executed_hnl),
		"paid_hnl": number(row.paid_hnl),
		"balance_hnl": number(row.balance_hnl),
		"retention_balance_hnl": number(row.retention_balance_hnl),
	}
