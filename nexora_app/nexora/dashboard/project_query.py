"""Resumen real de proyectos activos para el panel ejecutivo.

Reutiliza exactamente lo que ya existe y ya se prueba en otras partes del
panel — `budget_snapshot_as_of` (mismo cálculo que usa `_historical_budgets`
en `snapshot_query.py`) y `NXR Progress Record` (misma fuente que
`operational_query._progress_summary`) — en vez de inventar una nueva
lectura de presupuesto o de avance físico. No crea ningún DocType ni
servicio nuevo: es una agregación de solo lectura, acotada, sobre datos que
ya existen.
"""

from __future__ import annotations

from typing import Any

import frappe

from nexora.close.as_of import budget_snapshot_as_of
from nexora.dashboard.analytics_core import number

ACTIVE_PROJECT_STATUSES = ("Open",)
PROJECT_ROW_LIMIT = 8


def _latest_physical_percent(project: str) -> float:
	records = frappe.get_all(
		"NXR Progress Record",
		filters={"project": project, "status": "Approved"},
		fields=["progress_percent"],
		order_by="recorded_date desc, creation desc",
		limit=1,
	)
	return number(records[0]["progress_percent"]) if records else 0.0


def active_projects_summary(project: str | None, period_end: str) -> dict[str, Any]:
	"""Una sola fila cuando la vista ya está acotada a un proyecto (el mismo que
	`require_project_access` ya autorizó más arriba en `get_executive_snapshot`)
	— nunca se filtra una lista más amplia de la que el propio proyecto
	seleccionado permite ver. Sin proyecto seleccionado, `get_executive_snapshot`
	ya exige `view_all_projects` antes de llegar aquí, así que un listado
	acotado de proyectos activos no expone nada que el llamador no pudiera
	consultar ya de otra forma."""

	if project:
		projects = frappe.get_all("Project", filters={"name": project}, fields=["name", "project_name"])
		active_count = len(projects)
	else:
		projects = frappe.get_all(
			"Project",
			filters={"status": ["in", ACTIVE_PROJECT_STATUSES]},
			fields=["name", "project_name"],
			order_by="modified desc",
			limit=PROJECT_ROW_LIMIT,
		)
		active_count = int(frappe.db.count("Project", filters={"status": ["in", ACTIVE_PROJECT_STATUSES]}))

	rows = []
	for row in projects:
		budget = budget_snapshot_as_of(row["name"], period_end)
		rows.append(
			{
				"project": row["name"],
				"project_label": row.get("project_name") or row["name"],
				"physical_percent": _latest_physical_percent(row["name"]),
				"budget_hnl": number(budget.get("total_approved_hnl")),
				"executed_hnl": number(budget.get("total_executed_hnl")),
				"execution_percent": number(budget.get("utilization_percent")),
			}
		)
	average_execution_percent = (
		number(sum(row["execution_percent"] for row in rows) / len(rows)) if rows else 0.0
	)
	return {
		"active_count": active_count,
		"rows": rows,
		"average_execution_percent": average_execution_percent,
	}
