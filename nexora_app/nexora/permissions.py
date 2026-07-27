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
OPERATOR_ROLES = {
	"System Manager",
	"NEXORA Administrator",
	"NEXORA Finance Manager",
	"NEXORA Finance Operator",
}
MANAGER_ROLES = {"System Manager", "NEXORA Administrator", "NEXORA Finance Manager"}
SENSITIVE_DIRECTORY_ROLES = {
	"System Manager",
	"NEXORA Administrator",
	"NEXORA Finance Manager",
	"NEXORA Auditor",
}
ACTION_ROLES = {
	"preview": ACCESS_ROLES,
	"read_balances": ACCESS_ROLES,
	"read_entities": ACCESS_ROLES,
	"read_sensitive_entity": SENSITIVE_DIRECTORY_ROLES,
	"read_contracts": ACCESS_ROLES,
	"read_purchases": ACCESS_ROLES,
	"create_source": OPERATOR_ROLES,
	"cancel_source": MANAGER_ROLES,
	"execute": OPERATOR_ROLES,
	"upload_evidence": OPERATOR_ROLES,
	"create_entity": OPERATOR_ROLES,
	"create_contract": OPERATOR_ROLES,
	"create_supplier": OPERATOR_ROLES,
	"create_purchase_request": OPERATOR_ROLES,
	"submit_purchase_request": OPERATOR_ROLES,
	"update_entity": OPERATOR_ROLES,
	"approve": MANAGER_ROLES,
	"review_evidence": MANAGER_ROLES,
	"return": MANAGER_ROLES,
	"reclassify": MANAGER_ROLES,
	"manage_entity": MANAGER_ROLES,
	"manage_entity_role": MANAGER_ROLES,
	"manage_entity_compliance": MANAGER_ROLES,
	"consolidate_entity": MANAGER_ROLES,
	"manage_contract": MANAGER_ROLES,
	"execute_contract": MANAGER_ROLES,
	"manage_supplier": MANAGER_ROLES,
	"approve_purchase_request": MANAGER_ROLES,
}

ACTION_ROLE_LABELS = {
	"cancel_source": _("Gerente financiero o Administrador"),
	"approve": _("Gerente financiero o Administrador"),
	"execute": _("Operador financiero, Gerente financiero o Administrador"),
}


def can_access_nexora() -> bool:
	if frappe.session.user == "Guest":
		return False
	return bool(ACCESS_ROLES.intersection(frappe.get_roles(frappe.session.user)))


def require_action(action: str, user: str | None = None) -> None:
	actor = user or frappe.session.user
	if actor == "Guest":
		frappe.throw(_("Debe iniciar sesión para continuar."), frappe.PermissionError)
	allowed = ACTION_ROLES.get(action)
	if not allowed:
		frappe.throw(
			_("Esta función no está configurada correctamente. Comuníquese con el administrador."),
			frappe.PermissionError,
		)
	if not allowed.intersection(frappe.get_roles(actor)):
		required = ACTION_ROLE_LABELS.get(action, _("un rol autorizado de NEXORA"))
		frappe.throw(
			_("No puede realizar esta acción. Se requiere: {0}.").format(required),
			frappe.PermissionError,
		)
