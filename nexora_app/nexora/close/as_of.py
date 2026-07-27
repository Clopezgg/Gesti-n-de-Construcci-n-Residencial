from __future__ import annotations

from decimal import Decimal
from typing import Any

import frappe

from nexora.dashboard.analytics_core import number

UNCLASSIFIED = "Sin clasificar"


def _selected_budget_names(project: str | None, period_end: str) -> list[str]:
	rows = frappe.db.sql(
		"""
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
			AND newer.name IS NULL
			AND (%(project)s IS NULL OR b.project=%(project)s)
		ORDER BY b.project,b.effective_date DESC,b.version DESC,b.creation DESC
		""",
		{"project": project, "period_end": period_end},
		as_dict=True,
	)
	return [str(row.name) for row in rows]


def _category_labels(categories: set[str]) -> dict[str, str]:
	codes = sorted(category for category in categories if category != UNCLASSIFIED)
	if not codes:
		return {}
	rows = frappe.db.sql(
		"""
		SELECT name,code,category_name
		FROM `tabNXR Economic Category`
		WHERE name IN %(categories)s OR code IN %(categories)s
		""",
		{"categories": tuple(codes)},
		as_dict=True,
	)
	labels: dict[str, str] = {}
	for row in rows:
		label = str(row.category_name or row.code or row.name)
		labels[str(row.name)] = label
		if row.code:
			labels[str(row.code)] = label
	return labels


def budget_snapshot_as_of(
	project: str | None,
	period_end: str,
	*,
	economic_category: str | None = None,
	cost_center: str | None = None,
) -> dict[str, Any]:
	"""Return the applicable budget version and ledger effects at a historical cut-off."""
	budget_names = _selected_budget_names(project, period_end)
	approved_by_category: dict[str, Decimal] = {}
	params: dict[str, Any] = {
		"project": project,
		"period_end": period_end,
		"economic_category": economic_category,
		"cost_center": cost_center,
	}
	if budget_names:
		params["budgets"] = tuple(budget_names)
		approved_rows = frappe.db.sql(
			"""
			SELECT COALESCE(economic_category,'Sin clasificar') category,
				COALESCE(SUM(approved_hnl),0) approved_hnl
			FROM `tabNXR Budget Line`
			WHERE parent IN %(budgets)s
				AND (%(economic_category)s IS NULL OR economic_category=%(economic_category)s)
				AND (%(cost_center)s IS NULL OR cost_center=%(cost_center)s)
			GROUP BY COALESCE(economic_category,'Sin clasificar')
			""",
			params,
			as_dict=True,
		)
		approved_by_category = {
			str(row.category): Decimal(str(row.approved_hnl or 0)) for row in approved_rows
		}

	effect_rows = frappe.db.sql(
		"""
		SELECT COALESCE(e.economic_category,o.economic_category,'Sin clasificar') category,
			COALESCE(SUM(CASE
				WHEN o.operation_type IN ('Commitment Reserve','Commitment Release')
				THEN e.amount_hnl ELSE 0 END),0) committed_hnl,
			COALESCE(SUM(CASE
				WHEN o.operation_type NOT IN ('Commitment Reserve','Commitment Release')
				THEN e.amount_hnl ELSE 0 END),0) executed_hnl
		FROM `tabNXR Operation Effect` e
		INNER JOIN `tabNXR Operation` o ON o.name=e.operation
		WHERE e.dimension='Budget'
			AND o.status NOT IN ('Draft','Cancelled')
			AND o.operation_date<=%(period_end)s
			AND (%(project)s IS NULL OR COALESCE(e.project,o.project)=%(project)s)
			AND (
				%(economic_category)s IS NULL
				OR COALESCE(e.economic_category,o.economic_category)=%(economic_category)s
			)
			AND (%(cost_center)s IS NULL OR COALESCE(e.cost_center,o.cost_center)=%(cost_center)s)
		GROUP BY COALESCE(e.economic_category,o.economic_category,'Sin clasificar')
		""",
		params,
		as_dict=True,
	)
	committed_by_category = {
		str(row.category): max(Decimal(str(row.committed_hnl or 0)), Decimal("0")) for row in effect_rows
	}
	executed_by_category = {
		str(row.category): max(Decimal(str(row.executed_hnl or 0)), Decimal("0")) for row in effect_rows
	}
	categories = set(approved_by_category) | set(committed_by_category) | set(executed_by_category)
	labels = _category_labels(categories)
	lines: list[dict[str, Any]] = []
	for category in sorted(categories):
		approved = approved_by_category.get(category, Decimal("0"))
		committed = committed_by_category.get(category, Decimal("0"))
		executed = executed_by_category.get(category, Decimal("0"))
		lines.append(
			{
				"category": category,
				"label": labels.get(category, category),
				"approved_hnl": number(approved),
				"committed_hnl": number(committed),
				"executed_hnl": number(executed),
				"available_hnl": number(approved - committed - executed),
			}
		)

	approved = sum(approved_by_category.values(), Decimal("0"))
	committed = sum(committed_by_category.values(), Decimal("0"))
	executed = sum(executed_by_category.values(), Decimal("0"))
	used = committed + executed
	return {
		"budget_count": len(budget_names),
		"budget_names": budget_names,
		"total_approved_hnl": number(approved),
		"total_committed_hnl": number(committed),
		"total_executed_hnl": number(executed),
		"total_available_hnl": number(approved - used),
		"utilization_percent": number((used / approved * Decimal("100")) if approved else 0),
		"lines": lines,
		"basis": "Última versión presupuestaria vigente y efectos del Libro Central hasta la fecha de corte.",
		"filter_context": {
			"economic_category": economic_category,
			"cost_center": cost_center,
		},
	}


def budget_totals_as_of(project: str | None, period_end: str) -> dict[str, Any]:
	"""Return summary-only budget totals for immutable close snapshots."""
	result = budget_snapshot_as_of(project, period_end)
	result.pop("lines", None)
	return result
