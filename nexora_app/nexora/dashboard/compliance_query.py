from __future__ import annotations

from typing import Any

import frappe

from nexora.permissions import require_project_access

ITEM_LIMIT = 8
UPCOMING_WINDOW_DAYS = 30


def compliance_alerts(project: str | None) -> dict[str, Any]:
	"""Cumplimiento por vencer o ya vencido de las entidades con un rol activo en el
	proyecto consultado. `NXR Entity Compliance.status` es un estado que alguien
	transiciona a mano (`transition_entity_compliance`) y puede quedar desactualizado
	si nadie lo revisó; esta alerta calcula la urgencia siempre desde `valid_until`,
	nunca desde ese campo, para no depender de que alguien lo hubiera actualizado."""
	require_project_access(project, action="view_reports")
	rows = frappe.db.sql(
		"""
		SELECT DISTINCT comp.name,comp.document_number,comp.compliance_type,
			comp.valid_until,ent.name entity,ent.display_name entity_name,
			ent.entity_type,
			CASE
				WHEN comp.valid_until<%(today)s THEN 'Vencido'
				WHEN comp.valid_until<=DATE_ADD(%(today)s, INTERVAL %(window)s DAY) THEN 'Por vencer'
				ELSE 'Vigente'
			END compliance_state
		FROM `tabNXR Entity Compliance` comp
		INNER JOIN `tabNXR Entity` ent ON ent.name=comp.entity
		WHERE comp.status!='Approved Exception'
			AND comp.valid_until IS NOT NULL
			AND comp.valid_until<=DATE_ADD(%(today)s, INTERVAL %(window)s DAY)
			AND (
				%(project)s IS NULL
				OR EXISTS (
					SELECT 1 FROM `tabNXR Entity Role` role
					WHERE role.entity=comp.entity
						AND role.project=%(project)s
						AND role.status='Active'
				)
			)
		ORDER BY comp.valid_until
		LIMIT %(limit)s
		""",
		{
			"today": frappe.utils.today(),
			"window": UPCOMING_WINDOW_DAYS,
			"project": project,
			"limit": ITEM_LIMIT,
		},
		as_dict=True,
	)
	items = [dict(row) for row in rows]
	return {
		"items": items,
		"expired_count": sum(1 for row in items if row["compliance_state"] == "Vencido"),
		"upcoming_count": sum(1 for row in items if row["compliance_state"] == "Por vencer"),
		"window_days": UPCOMING_WINDOW_DAYS,
		"basis": (
			"Cumplimiento de entidades con un rol activo en el proyecto, con vencimiento "
			"calculado desde la fecha, no desde el estado transicionado a mano."
		),
	}
