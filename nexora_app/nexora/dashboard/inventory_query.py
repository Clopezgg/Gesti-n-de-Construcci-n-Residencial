from __future__ import annotations

from typing import Any

import frappe


def critical_inventory(project: str | None) -> list[dict[str, Any]]:
	rows = frappe.db.sql(
		"""
		SELECT l.item,l.warehouse,COALESCE(SUM(CASE
			WHEN t.transaction_type IN ('Receipt','Transfer In','Return') THEN l.quantity
			WHEN t.transaction_type IN ('Transfer Out','Issue to Contractor','Consumption','Damage','Loss') THEN -l.quantity
			ELSE 0 END),0) balance_qty
		FROM `tabNXR Stock Transaction Line` l
		INNER JOIN `tabNXR Stock Transaction` t ON t.name=l.parent
		WHERE t.status='Completed'
			AND (%(project)s IS NULL OR t.project=%(project)s)
		GROUP BY l.item,l.warehouse HAVING balance_qty<=0
		ORDER BY balance_qty ASC,l.item ASC LIMIT 8
		""",
		{"project": project},
		as_dict=True,
	)
	return [
		{"item": row.item, "warehouse": row.warehouse, "balance_qty": float(row.balance_qty)} for row in rows
	]
