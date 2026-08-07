from __future__ import annotations

from typing import Any

import frappe

from nexora.dashboard.service import _get_all, _project_filters
from nexora.permissions import require_project_access

ITEM_LIMIT = 8

# Estados en los que un documento cambió de mano por una decisión, no por edición de
# borrador. `NXR Operation` no lleva una bitácora de transiciones propia; `modified`/
# `modified_by` es la aproximación que ya usa el resto del panel para "actividad
# reciente" (`_recent_operations`), así que esta zona reutiliza la misma fuente en vez
# de inventar un mecanismo de auditoría distinto.
DECISIVE_STATUSES = (
	"Approved",
	"Rejected",
	"Executed",
	"Compensated Partial",
	"Compensated Total",
	"Cancelled",
)

# Cuando el estado final tiene un campo de actor dedicado, ese actor es más preciso que
# `modified_by`: alguien puede reabrir y volver a guardar un documento ya aprobado sin
# haber sido quien lo aprobó.
ACTOR_FIELD_BY_STATUS = {
	"Approved": "approved_by",
	"Executed": "executed_by",
}


def team_activity(project: str | None, *, user: str | None = None) -> dict[str, Any]:
	"""Qué hicieron otros usuarios recientemente: aprobar, rechazar, contabilizar,
	corregir o anular una operación del proyecto consultado. Excluye al propio usuario
	-esta zona responde "qué hizo el resto del equipo", no un historial personal-.

	`status` viaja sin traducir: `nexora_dashboard.js` ya mantiene el diccionario
	`statusLabels` para este mismo campo de `NXR Operation` (lo usa `_recent_operations`
	desde hace tiempo); duplicarlo aquí en español lo dejaría divergiendo la primera vez
	que alguien retocara el texto en un solo lado."""
	actor = user or frappe.session.user
	require_project_access(project, action="view_reports")
	filters: dict[str, Any] = {
		**_project_filters(project),
		"status": ["in", list(DECISIVE_STATUSES)],
		"modified_by": ["!=", actor],
	}
	rows = _get_all(
		"NXR Operation",
		fields=[
			"name",
			"document_number",
			"status",
			"operation_type",
			"project",
			"modified",
			"modified_by",
			"approved_by",
			"executed_by",
		],
		filters=filters,
		order_by="modified desc",
		limit=ITEM_LIMIT,
	)
	actor_names: set[str] = set()
	for row in rows:
		actor_field = ACTOR_FIELD_BY_STATUS.get(str(row.get("status")))
		actor_user = (row.get(actor_field) if actor_field else None) or row.get("modified_by")
		if actor_user:
			actor_names.add(str(actor_user))
	full_names = _full_names(actor_names)
	items = []
	for row in rows:
		status = str(row.get("status"))
		actor_field = ACTOR_FIELD_BY_STATUS.get(status)
		actor_user = str((row.get(actor_field) if actor_field else None) or row.get("modified_by") or "")
		items.append(
			{
				"name": row.get("name"),
				"document_number": row.get("document_number"),
				"status": status,
				"operation_type": row.get("operation_type"),
				"project": row.get("project"),
				"modified": row.get("modified"),
				"actor": actor_user,
				"actor_label": full_names.get(actor_user, actor_user),
			}
		)
	return {
		"items": items,
		"basis": (
			"Últimas operaciones con una decisión tomada por otro usuario -aprobar, "
			"rechazar, contabilizar, corregir o anular- en el proyecto consultado."
		),
	}


def _full_names(user_names: set[str]) -> dict[str, str]:
	if not user_names:
		return {}
	rows = frappe.get_all(
		"User",
		filters={"name": ["in", list(user_names)]},
		fields=["name", "full_name"],
	)
	return {str(row["name"]): str(row["full_name"] or row["name"]) for row in rows}
