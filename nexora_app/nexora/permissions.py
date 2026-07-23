from __future__ import annotations

import frappe
from frappe import _

ACCESS_ROLES = {
	"System Manager",
	"NEXORA Administrator",
	"NEXORA Finance Manager",
	"NEXORA Finance Operator",
	"NEXORA Auditor",
	"NEXORA Project Viewer",
}
ACTION_ROLES = {
	"preview": ACCESS_ROLES,
	"read_balances": ACCESS_ROLES,
	"create_source": {
		"System Manager",
		"NEXORA Administrator",
		"NEXORA Finance Manager",
		"NEXORA Finance Operator",
	},
	"execute": {
		"System Manager",
		"NEXORA Administrator",
		"NEXORA Finance Manager",
		"NEXORA Finance Operator",
	},
	"approve": {"System Manager", "NEXORA Administrator", "NEXORA Finance Manager"},
	"return": {"System Manager", "NEXORA Administrator", "NEXORA Finance Manager"},
	"reclassify": {"System Manager", "NEXORA Administrator", "NEXORA Finance Manager"},
}


def can_access_nexora() -> bool:
	if frappe.session.user == "Guest":
		return False
	return bool(ACCESS_ROLES.intersection(frappe.get_roles(frappe.session.user)))


def require_action(action: str, user: str | None = None) -> None:
	actor = user or frappe.session.user
	if actor == "Guest":
		frappe.throw(_("Autenticación requerida."), frappe.PermissionError)
	allowed = ACTION_ROLES.get(action)
	if not allowed:
		frappe.throw(_("Acción NEXORA desconocida: {0}.").format(action), frappe.PermissionError)
	if not allowed.intersection(frappe.get_roles(actor)):
		frappe.throw(
			_("El usuario no tiene permiso de servidor para {0}.").format(action), frappe.PermissionError
		)
