"""Lógica pura de administración funcional de NEXORA — sin Frappe, sin red.

Constitución Cap. 14 (enmienda del propietario, 2026-08-16): NEXORA necesita
una zona propia para administrar usuarios, roles, activación y desactivación,
separada de la cuenta técnica ``Administrator`` de Frappe. Este módulo fija
las dos reglas que deben cumplirse sin excepción antes de que
``nexora.administration.service`` toque un ``User`` real:

1. Solo los cinco roles de NEXORA son administrables desde esta pantalla —
   nunca ``System Manager`` ni cualquier otro rol técnico de Frappe/ERPNext,
   que seguiría gestionándose, si hace falta, desde el escritorio técnico.
2. Nunca puede quedar NEXORA sin ningún Administrador habilitado: sería un
   bloqueo real, sin forma de recuperarse desde la propia interfaz de NEXORA.
"""

from __future__ import annotations

ADMINISTRATOR_ROLE = "NEXORA Administrator"

ALLOWED_NEXORA_ROLES = frozenset(
	{
		ADMINISTRATOR_ROLE,
		"NEXORA Finance Manager",
		"NEXORA Finance Operator",
		"NEXORA Auditor",
		"NEXORA Project Viewer",
	}
)


class AdministrationError(Exception):
	"""Violación de una regla de administración funcional de NEXORA."""


def assert_manageable_role(role: str) -> None:
	if role not in ALLOWED_NEXORA_ROLES:
		raise AdministrationError(f"«{role}» no es un rol de NEXORA administrable desde esta pantalla.")


def assert_not_last_administrator(
	*,
	active_administrators: list[str],
	target_user: str,
	target_will_remain_administrator: bool,
) -> None:
	"""``active_administrators`` es la lista de usuarios hoy habilitados con el
	rol de Administrador NEXORA. Si la acción sobre ``target_user`` no le deja
	ese rol (se desactiva su cuenta, o se le revoca el rol), y quitarlo de la
	lista deja la lista vacía, la acción se rechaza."""

	if target_will_remain_administrator:
		return
	remaining = [user for user in active_administrators if user != target_user]
	if not remaining:
		raise AdministrationError(
			"No puede quitar el último Administrador NEXORA activo: el sistema "
			"quedaría sin nadie que pueda administrar usuarios."
		)


def normalize_role_selection(requested_roles: object) -> set[str]:
	if not isinstance(requested_roles, list):
		raise AdministrationError("La lista de roles debe enviarse como una lista.")
	normalized = {str(role).strip() for role in requested_roles if str(role).strip()}
	for role in normalized:
		assert_manageable_role(role)
	return normalized
