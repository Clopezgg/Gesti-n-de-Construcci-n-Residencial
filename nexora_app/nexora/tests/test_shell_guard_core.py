"""Pruebas de unidad reales de `nexora.shell_guard_core` — sin Frappe, sin red, sin
base de datos. Ejecuta lógica real con entradas reales (Bloque 154).

Máxima cautela aquí a propósito: un error en cualquier dirección tiene consecuencias
reales — dejar pasar es un hallazgo de seguridad sin corregir, bloquear de más es
dejar sin acceso al Desk a quien lo administra de verdad."""

from __future__ import annotations

import unittest

from nexora.shell_guard_core import (
	ACCESS_ROLES,
	ADMINISTRATOR_ONLY_ROLES,
	NEXORA_HOME,
	resolve_redirect,
)

NON_ADMIN_NEXORA_ROLES = ACCESS_ROLES - ADMINISTRATOR_ONLY_ROLES


class TestRoleSets(unittest.TestCase):
	def test_the_six_access_roles_are_exactly_the_documented_set(self) -> None:
		self.assertEqual(
			{
				"System Manager",
				"NEXORA Administrator",
				"NEXORA Finance Manager",
				"NEXORA Finance Operator",
				"NEXORA Auditor",
				"NEXORA Project Viewer",
			},
			ACCESS_ROLES,
		)

	def test_only_system_manager_and_nexora_administrator_are_exempt(self) -> None:
		self.assertEqual({"System Manager", "NEXORA Administrator"}, ADMINISTRATOR_ONLY_ROLES)

	def test_four_roles_remain_restricted(self) -> None:
		self.assertEqual(
			{
				"NEXORA Finance Manager",
				"NEXORA Finance Operator",
				"NEXORA Auditor",
				"NEXORA Project Viewer",
			},
			NON_ADMIN_NEXORA_ROLES,
		)


class TestAdministratorsAreNeverRedirected(unittest.TestCase):
	"""El fallo más caro posible: bloquear a quien administra la instalación de verdad."""

	def test_system_manager_reaches_any_desk_path(self) -> None:
		for path in ("/app/user", "/app/user-permission", "/app/workspace", "/app/setup-wizard"):
			with self.subTest(path=path):
				self.assertIsNone(resolve_redirect(path, {"System Manager"}))

	def test_nexora_administrator_reaches_any_desk_path(self) -> None:
		for path in ("/app/user", "/app/user-permission", "/app/workspace"):
			with self.subTest(path=path):
				self.assertIsNone(resolve_redirect(path, {"NEXORA Administrator"}))

	def test_a_user_holding_both_an_admin_role_and_a_restricted_role_is_exempt(self) -> None:
		self.assertIsNone(
			resolve_redirect("/app/user", {"NEXORA Administrator", "NEXORA Finance Operator"})
		)

	def test_system_manager_combined_with_a_restricted_role_is_exempt(self) -> None:
		self.assertIsNone(resolve_redirect("/app/user", {"System Manager", "NEXORA Auditor"}))


class TestRestrictedRolesBounceFromBareDeskPaths(unittest.TestCase):
	def test_each_restricted_role_alone_bounces_from_a_raw_doctype_list(self) -> None:
		for role in NON_ADMIN_NEXORA_ROLES:
			with self.subTest(role=role):
				self.assertEqual(NEXORA_HOME, resolve_redirect("/app/user", {role}))

	def test_bounces_from_a_workspace_path(self) -> None:
		self.assertEqual(NEXORA_HOME, resolve_redirect("/app/workspace", {"NEXORA Finance Manager"}))

	def test_bounces_from_a_settings_path(self) -> None:
		self.assertEqual(NEXORA_HOME, resolve_redirect("/app/user-permission", {"NEXORA Auditor"}))

	def test_bounces_regardless_of_path_case(self) -> None:
		self.assertEqual(NEXORA_HOME, resolve_redirect("/APP/USER", {"NEXORA Finance Manager"}))

	def test_bounces_with_a_trailing_slash(self) -> None:
		self.assertEqual(NEXORA_HOME, resolve_redirect("/app/user/", {"NEXORA Finance Manager"}))

	def test_bounces_with_a_query_string(self) -> None:
		self.assertEqual(
			NEXORA_HOME, resolve_redirect("/app/user?some=value", {"NEXORA Finance Manager"})
		)


class TestRestrictedRolesReachTheirOwnScreens(unittest.TestCase):
	def test_each_restricted_role_reaches_a_nexora_page(self) -> None:
		for role in NON_ADMIN_NEXORA_ROLES:
			with self.subTest(role=role):
				self.assertIsNone(resolve_redirect("/app/nexora-finance", {role}))

	def test_reaches_the_bare_app_root(self) -> None:
		self.assertIsNone(resolve_redirect("/app", {"NEXORA Finance Manager"}))

	def test_reaches_the_bare_app_root_with_a_trailing_slash(self) -> None:
		self.assertIsNone(resolve_redirect("/app/", {"NEXORA Finance Manager"}))

	def test_landing_on_its_own_home_never_redirects_again(self) -> None:
		"""Si esto alguna vez devolviera un destino, la guarda de cliente entraría en
		un bucle infinito de redirecciones sobre su propio destino."""
		self.assertIsNone(resolve_redirect(NEXORA_HOME, {"NEXORA Finance Manager"}))


class TestRestrictedRolesReachRealNxrDoctypeLinks(unittest.TestCase):
	"""Varias pantallas ya enlazan de verdad a estos DocType vía
	`frappe.utils.get_form_link()` — bloquearlos habría sido una regresión real, no
	una guarda nueva."""

	def test_reaches_an_nxr_contract_form(self) -> None:
		self.assertIsNone(resolve_redirect("/app/nxr-contract/CONTRACT-001", {"NEXORA Auditor"}))

	def test_reaches_an_nxr_operation_form(self) -> None:
		self.assertIsNone(
			resolve_redirect("/app/nxr-operation/OP-001", {"NEXORA Finance Operator"})
		)

	def test_reaches_an_nxr_fund_source_form(self) -> None:
		self.assertIsNone(
			resolve_redirect("/app/nxr-fund-source/FUND-001", {"NEXORA Finance Manager"})
		)

	def test_reaches_a_bare_nxr_doctype_list_too(self) -> None:
		self.assertIsNone(resolve_redirect("/app/nxr-contract", {"NEXORA Auditor"}))


class TestOutOfScopeRequestsAreNeverTouched(unittest.TestCase):
	def test_a_user_with_no_nexora_role_at_all_is_never_redirected(self) -> None:
		self.assertIsNone(resolve_redirect("/app/user", {"Purchase Manager"}))

	def test_an_empty_role_set_is_never_redirected(self) -> None:
		self.assertIsNone(resolve_redirect("/app/user", set()))

	def test_a_non_desk_path_is_never_touched(self) -> None:
		for path in ("/api/method/login", "/login", "/", "/assets/nexora/css/nexora.css"):
			with self.subTest(path=path):
				self.assertIsNone(resolve_redirect(path, {"NEXORA Finance Manager"}))

	def test_an_empty_path_is_never_touched(self) -> None:
		self.assertIsNone(resolve_redirect("", {"NEXORA Finance Manager"}))


if __name__ == "__main__":
	unittest.main()
