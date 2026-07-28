from __future__ import annotations

import frappe
from frappe import _

from nexora.financial.context import service_write


def record_operation_metadata(
	operation: str,
	movement_code: str,
	financial_account: str | None = None,
) -> None:
	existing = frappe.db.get_value(
		"NXR Operation Metadata",
		{"operation": operation},
		["name", "movement_code"],
		as_dict=True,
	)
	if existing:
		if str(existing.movement_code) != movement_code:
			frappe.throw(_("La operación ya conserva un código operativo diferente."))
		return
	with service_write():
		frappe.get_doc(
			{
				"doctype": "NXR Operation Metadata",
				"operation": operation,
				"movement_code": movement_code,
				"financial_account": financial_account,
			}
		).insert(ignore_permissions=True)
