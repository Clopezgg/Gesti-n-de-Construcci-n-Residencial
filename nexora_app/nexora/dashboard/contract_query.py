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
	conditions = [
		"c.status!='Cancelled Before Active'",
		"c.start_date<=%(end)s",
		"(c.current_end_date IS NULL OR c.current_end_date>=%(start)s)",
	]
	params: dict[str, Any] = {"start": start, "end": end}
	for fieldname, column, value in (
		("project", "c.project", project),
		("contract", "c.name", _text(data, "contract")),
		("contractor", "c.contractor", _text(data, "contractor")),
		("contract_status", "c.status", _text(data, "contract_status")),
	):
		if value:
			conditions.append(f"{column}=%({fieldname})s")
			params[fieldname] = value
	row = frappe.db.sql(
		f"""
		SELECT COUNT(*) contract_count,
			COALESCE(SUM(c.current_amount*COALESCE(c.exchange_rate,1)),0) contract_value_hnl,
			COALESCE(SUM(c.executed_amount*COALESCE(c.exchange_rate,1)),0) executed_hnl,
			COALESCE(SUM(c.paid_amount*COALESCE(c.exchange_rate,1)),0) paid_hnl,
			COALESCE(SUM(c.pending_amount*COALESCE(c.exchange_rate,1)),0) balance_hnl,
			COALESCE(SUM(c.retention_balance*COALESCE(c.exchange_rate,1)),0)
				retention_balance_hnl
		FROM `tabNXR Contract` c
		WHERE {" AND ".join(conditions)}
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
