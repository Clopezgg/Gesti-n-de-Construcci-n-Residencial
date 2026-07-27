from __future__ import annotations

from decimal import Decimal
from typing import Any

import frappe

from nexora.dashboard.analytics_core import number


def _selected_budget_names(project: str | None, period_end: str) -> list[str]:
	project_sql = "AND b.project=%(project)s" if project else ""
	rows = frappe.db.sql(
		f"""
		SELECT b.name
		FROM `tabNXR Budget` b
		LEFT JOIN `tabNXR Budget` newer
			ON newer.project=b.project
			AND newer.status NOT IN ('Draft','Cancelled')
			AND newer.effective_date<=%(period_end)s
			AND (
				newer.effective_date>b.effective_date
				OR (newer.effective_date=b.effective_date AND newer.version>b.version)
				OR (
					newer.effective_date=b.effective_date
					AND newer.version=b.version
					AND newer.creation>b.creation
				)
			)
		WHERE b.status NOT IN ('Draft','Cancelled')
			AND b.effective_date<=%(period_end)s
			AND newer.name IS NULL {project_sql}
		ORDER BY b.project,b.effective_date DESC,b.version DESC,b.creation DESC
		""",
		{"project": project, "period_end": period_end},
		as_dict=True,
	)
	return [str(row.name) for row in rows]


def budget_totals_as_of(project: str | None, period_end: str) -> dict[str, Any]:
	"""Return approved, committed and executed budget totals at a historical cut-off."""
	budget_names = _selected_budget_names(project, period_end)
	approved = Decimal("0")
	if budget_names:
		approved = Decimal(
			str(
				frappe.db.sql(
					"""
					SELECT COALESCE(SUM(approved_hnl),0)
					FROM `tabNXR Budget Line`
					WHERE parent IN %(budgets)s
					""",
					{"budgets": tuple(budget_names)},
				)[0][0]
				or 0
			)
		)
	project_sql = "AND COALESCE(e.project,o.project)=%(project)s" if project else ""
	row = frappe.db.sql(
		f"""
		SELECT
			COALESCE(SUM(CASE
				WHEN e.dimension='Budget'
					AND o.operation_type IN ('Commitment Reserve','Commitment Release')
				THEN e.amount_hnl ELSE 0 END),0) committed_hnl,
			COALESCE(SUM(CASE
				WHEN e.dimension='Budget'
					AND o.operation_type NOT IN ('Commitment Reserve','Commitment Release')
				THEN e.amount_hnl ELSE 0 END),0) executed_hnl
		FROM `tabNXR Operation Effect` e
		INNER JOIN `tabNXR Operation` o ON o.name=e.operation
		WHERE o.status NOT IN ('Draft','Cancelled')
			AND o.operation_date<=%(period_end)s {project_sql}
		""",
		{"project": project, "period_end": period_end},
		as_dict=True,
	)[0]
	committed = max(Decimal(str(row.committed_hnl or 0)), Decimal("0"))
	executed = max(Decimal(str(row.executed_hnl or 0)), Decimal("0"))
	return {
		"budget_count": len(budget_names),
		"budget_names": budget_names,
		"total_approved_hnl": number(approved),
		"total_committed_hnl": number(committed),
		"total_executed_hnl": number(executed),
		"total_available_hnl": number(approved - committed - executed),
		"basis": "Última versión presupuestaria vigente por proyecto y efectos del Libro Central hasta la fecha de cierre.",
	}
