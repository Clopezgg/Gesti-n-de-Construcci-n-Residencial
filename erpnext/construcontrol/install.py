from __future__ import annotations

import frappe


ROLES = (
	"ConstruControl Manager",
	"ConstruControl Auditor",
	"ConstruControl Operator",
	"ConstruControl Viewer",
)


def after_migrate() -> None:
	"""Create extension roles without changing ERPNext's standard roles."""
	for role_name in ROLES:
		if frappe.db.exists("Role", role_name):
			continue
		frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1}).insert(
			ignore_permissions=True
		)
