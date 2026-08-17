"""Administración funcional de NEXORA: usuarios, roles y su bitácora.

Constitución Cap. 14 (enmienda del propietario, 2026-08-16): existe una zona
propia de NEXORA para administrar usuarios, roles, activación y
desactivación, separada de la cuenta técnica ``Administrator`` de Frappe.

Este módulo no reimplementa la gestión de usuarios de Frappe — ``User`` y
``Has Role`` ya son DocTypes maduros, probados y con su propio modelo de
permisos. Es un envoltorio delgado y auditado, restringido a los cinco roles
de NEXORA (``nexora.administration.core.ALLOWED_NEXORA_ROLES``): nunca
``System Manager`` ni cualquier otro rol técnico de Frappe/ERPNext, que sigue
gestionándose, si hace falta, desde el escritorio técnico — la cuenta
``Administrator`` misma queda excluida de estas pantallas a propósito, para
que la administración empresarial de NEXORA nunca dependa de ella.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.administration.core import (
	ADMINISTRATOR_ROLE,
	ALLOWED_NEXORA_ROLES,
	AdministrationError,
	assert_not_last_administrator,
	normalize_role_selection,
)
from nexora.financial.context import service_write
from nexora.financial.core import canonical_payload_hash
from nexora.financial.db import audit, correlation, parse_payload
from nexora.permissions import require_action

AUDIT_DOCTYPE = "User"
_EXCLUDED_ACCOUNTS = ("Administrator", "Guest")


def _active_nexora_administrators() -> list[str]:
	holders = frappe.get_all(
		"Has Role",
		filters={"role": ADMINISTRATOR_ROLE, "parenttype": "User"},
		pluck="parent",
	)
	if not holders:
		return []
	return frappe.get_all(
		"User",
		filters={"name": ["in", holders], "enabled": 1},
		pluck="name",
	)


def _user_roles(user: str) -> list[str]:
	roles = frappe.get_all("Has Role", filters={"parent": user, "parenttype": "User"}, pluck="role")
	return sorted(role for role in roles if role in ALLOWED_NEXORA_ROLES)


def _require_existing_user(user: str) -> None:
	if not user:
		frappe.throw(_("Seleccione el usuario."))
	if user in _EXCLUDED_ACCOUNTS:
		frappe.throw(_("La cuenta técnica «{0}» no se administra desde esta pantalla.").format(user))
	if not frappe.db.exists("User", user):
		frappe.throw(_("El usuario indicado no existe."))


@frappe.whitelist(methods=["POST"])
def list_users(payload: str | Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
	require_action("view_users")
	data = parse_payload(payload or {})
	filters: dict[str, Any] = {"name": ["not in", list(_EXCLUDED_ACCOUNTS)]}
	status = data.get("status")
	if status == "Active":
		filters["enabled"] = 1
	elif status == "Inactive":
		filters["enabled"] = 0
	users = frappe.get_all(
		"User",
		filters=filters,
		fields=["name", "full_name", "email", "enabled", "last_login"],
		order_by="full_name asc",
		limit_page_length=min(max(int(data.get("limit") or 200), 1), 500),
	)
	return [{**user, "nexora_roles": _user_roles(user["name"])} for user in users]


@frappe.whitelist(methods=["POST"])
def list_nexora_roles(payload: str | Mapping[str, Any] | None = None) -> list[dict[str, str]]:
	require_action("view_users")
	return [
		{
			"role": ADMINISTRATOR_ROLE,
			"label": _("Administrador NEXORA"),
			"description": _("Administra usuarios, roles y configuración de NEXORA."),
		},
		{
			"role": "NEXORA Finance Manager",
			"label": _("Gerente financiero"),
			"description": _("Aprueba, cierra y gestiona el núcleo financiero."),
		},
		{
			"role": "NEXORA Finance Operator",
			"label": _("Operador financiero"),
			"description": _("Ejecuta operaciones diarias sin permisos de aprobación."),
		},
		{
			"role": "NEXORA Auditor",
			"label": _("Auditor"),
			"description": _("Consulta trazabilidad y evidencia sin permisos de escritura."),
		},
		{
			"role": "NEXORA Project Viewer",
			"label": _("Visor de proyecto"),
			"description": _("Consulta reportes del proyecto asignado."),
		},
	]


@frappe.whitelist(methods=["POST"])
def set_user_status(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("manage_users")
	target_user = str(data.get("user") or "").strip()
	_require_existing_user(target_user)
	enabled = bool(data.get("enabled"))
	if target_user == frappe.session.user and not enabled:
		frappe.throw(_("No puede desactivar su propia sesión desde aquí."))
	if not enabled:
		try:
			assert_not_last_administrator(
				active_administrators=_active_nexora_administrators(),
				target_user=target_user,
				target_will_remain_administrator=False,
			)
		except AdministrationError as exc:
			frappe.throw(str(exc))

	correlation_id = correlation(data)
	fingerprint = canonical_payload_hash({"user": target_user, "enabled": enabled})
	with service_write():
		doc = frappe.get_doc("User", target_user)
		doc.enabled = 1 if enabled else 0
		doc.save(ignore_permissions=True)
	audit(
		"nexora_user_status_changed",
		AUDIT_DOCTYPE,
		target_user,
		fingerprint,
		correlation_id,
		{"enabled": enabled, "changed_by": frappe.session.user},
	)
	return {"user": target_user, "enabled": enabled}


@frappe.whitelist(methods=["POST"])
def set_user_roles(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Reemplaza el conjunto de roles NEXORA de ``user`` con exactamente
	``roles``. Nunca toca ningún rol fuera de ``ALLOWED_NEXORA_ROLES`` que el
	usuario ya tuviera (``System Manager`` u otro rol técnico de Frappe/
	ERPNext permanece intacto): esta pantalla administra la capa de NEXORA,
	no la de Frappe."""

	data = parse_payload(payload)
	require_action("manage_users")
	target_user = str(data.get("user") or "").strip()
	_require_existing_user(target_user)
	try:
		normalized_roles = normalize_role_selection(data.get("roles"))
	except AdministrationError as exc:
		frappe.throw(str(exc))

	if ADMINISTRATOR_ROLE not in normalized_roles:
		try:
			assert_not_last_administrator(
				active_administrators=_active_nexora_administrators(),
				target_user=target_user,
				target_will_remain_administrator=False,
			)
		except AdministrationError as exc:
			frappe.throw(str(exc))

	correlation_id = correlation(data)
	fingerprint = canonical_payload_hash({"user": target_user, "roles": sorted(normalized_roles)})
	current_roles = set(_user_roles(target_user))
	to_add = normalized_roles - current_roles
	to_remove = (current_roles - normalized_roles) & ALLOWED_NEXORA_ROLES
	with service_write():
		doc = frappe.get_doc("User", target_user)
		for role in to_add:
			doc.append("roles", {"role": role})
		if to_remove:
			doc.roles = [row for row in doc.roles if row.role not in to_remove]
		doc.save(ignore_permissions=True)
	audit(
		"nexora_user_roles_changed",
		AUDIT_DOCTYPE,
		target_user,
		fingerprint,
		correlation_id,
		{"roles": sorted(normalized_roles), "changed_by": frappe.session.user},
	)
	return {"user": target_user, "roles": sorted(normalized_roles)}


@frappe.whitelist(methods=["POST"])
def list_recent_activity(payload: str | Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
	require_action("view_users")
	data = parse_payload(payload or {})
	rows = frappe.get_all(
		"NXR Audit Event",
		filters={"reference_doctype": AUDIT_DOCTYPE},
		fields=["event_type", "reference_name", "actor", "creation", "after_json"],
		order_by="creation desc",
		limit_page_length=min(max(int(data.get("limit") or 50), 1), 200),
	)
	return list(rows)
