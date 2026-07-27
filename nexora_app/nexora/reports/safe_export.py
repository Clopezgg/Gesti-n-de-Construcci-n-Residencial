from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.dashboard.executive import get_contract_page, get_source_statement_page
from nexora.dashboard.expense_query import get_expense_page
from nexora.reports.service import (
	EXPORT_ROW_LIMIT,
	_data,
	_project,
	_report_code,
	export_report as canonical_export_report,
)

PAGINATED_REPORT_LOADERS = {
	"FI01": get_source_statement_page,
	"FI02": get_expense_page,
	"CO01": get_contract_page,
}


def _assert_export_size(data: Mapping[str, Any], report_code: str) -> None:
	loader = PAGINATED_REPORT_LOADERS.get(report_code)
	if not loader:
		return
	page = loader({**data, "page": 1, "page_size": 1})
	total = int(page.get("pagination", {}).get("total") or 0)
	if total > EXPORT_ROW_LIMIT:
		frappe.throw(
			_("El reporte contiene {0} filas y supera el límite autorizado de {1}.").format(
				total,
				EXPORT_ROW_LIMIT,
			)
		)


@frappe.whitelist(methods=["POST"])
def export_report(payload: str | Mapping[str, Any]) -> None:
	"""Preflight canonical exports so oversized reports are rejected, never truncated."""
	data = _data(payload)
	_project(data, "export_reports")
	code = _report_code(data)
	_assert_export_size(data, code)
	return canonical_export_report(data)
