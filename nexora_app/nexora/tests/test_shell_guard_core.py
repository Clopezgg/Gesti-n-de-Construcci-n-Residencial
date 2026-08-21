"""Pruebas de unidad reales de `nexora.shell_guard_core` — sin Frappe, sin red, sin
base de datos. Ejecuta lógica real con entradas reales (Bloque 154, corregida en
CORRECCIÓN ESTRUCTURAL DEL DESK FRAPPE).

Máxima cautela aquí a propósito: un error en cualquier dirección tiene consecuencias
reales — dejar pasar es la fuga real de UX genérica de Frappe/ERPNext que este mismo
bloque corrige (el usuario real "Administrator" cayendo en el Workspace "Home" con
"Let's begin your journey with ERPNext"); bloquear de más rompe un enlace real del
producto (`get_form_link`) a un documento de NEXORA."""

from __future__ import annotations

import unittest

from nexora.shell_guard_core import ACCESS_ROLES, NEXORA_HOME, resolve_redirect


class TestAccessRoles(unittest.TestCase):
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


class TestNoRoleIsExemptFromTheGuardAnymore(unittest.TestCase):
	"""Hallazgo real corregido en este bloque: `System Manager`/`NEXORA Administrator`
	estaban completamente exentos — por eso el usuario real "Administrator" (que
	siempre tiene `System Manager`) caía en el Desk crudo de ERPNext sin ningún
	filtro. Ya no existe ninguna excepción de rol."""

	def test_system_manager_alone_bounces_from_a_raw_doctype_list(self) -> None:
		self.assertEqual(NEXORA_HOME, resolve_redirect("/app/user", {"System Manager"}))

	def test_nexora_administrator_alone_bounces_from_a_raw_doctype_list(self) -> None:
		self.assertEqual(NEXORA_HOME, resolve_redirect("/app/user", {"NEXORA Administrator"}))

	def test_system_manager_bounces_from_the_generic_home_workspace(self) -> None:
		"""La ruta real que muestra "Let's begin your journey with ERPNext"."""
		self.assertEqual(NEXORA_HOME, resolve_redirect("/app/home", {"System Manager"}))

	def test_nexora_administrator_bounces_from_the_generic_home_workspace(self) -> None:
		self.assertEqual(NEXORA_HOME, resolve_redirect("/app/home", {"NEXORA Administrator"}))

	def test_system_manager_bounces_from_a_generic_workspace(self) -> None:
		self.assertEqual(NEXORA_HOME, resolve_redirect("/app/workspace", {"System Manager"}))

	def test_a_user_holding_both_an_admin_role_and_a_restricted_role_still_bounces(self) -> None:
		self.assertEqual(
			NEXORA_HOME,
			resolve_redirect("/app/user", {"NEXORA Administrator", "NEXORA Finance Operator"}),
		)

	def test_system_manager_combined_with_a_restricted_role_still_bounces(self) -> None:
		self.assertEqual(NEXORA_HOME, resolve_redirect("/app/user", {"System Manager", "NEXORA Auditor"}))


class TestRestrictedRolesBounceFromBareDeskPaths(unittest.TestCase):
	NON_ADMIN_NEXORA_ROLES = (
		"NEXORA Finance Manager",
		"NEXORA Finance Operator",
		"NEXORA Auditor",
		"NEXORA Project Viewer",
	)

	def test_each_restricted_role_alone_bounces_from_a_raw_doctype_list(self) -> None:
		for role in self.NON_ADMIN_NEXORA_ROLES:
			with self.subTest(role=role):
				self.assertEqual(NEXORA_HOME, resolve_redirect("/app/user", {role}))

	def test_bounces_from_a_workspace_path(self) -> None:
		self.assertEqual(NEXORA_HOME, resolve_redirect("/app/workspace", {"NEXORA Finance Manager"}))

	def test_bounces_from_the_generic_home_workspace(self) -> None:
		self.assertEqual(NEXORA_HOME, resolve_redirect("/app/home", {"NEXORA Finance Manager"}))

	def test_bounces_from_a_settings_path(self) -> None:
		self.assertEqual(NEXORA_HOME, resolve_redirect("/app/user-permission", {"NEXORA Auditor"}))

	def test_bounces_regardless_of_path_case(self) -> None:
		self.assertEqual(NEXORA_HOME, resolve_redirect("/APP/USER", {"NEXORA Finance Manager"}))

	def test_bounces_with_a_trailing_slash(self) -> None:
		self.assertEqual(NEXORA_HOME, resolve_redirect("/app/user/", {"NEXORA Finance Manager"}))

	def test_bounces_with_a_query_string(self) -> None:
		self.assertEqual(NEXORA_HOME, resolve_redirect("/app/user?some=value", {"NEXORA Finance Manager"}))

	def test_bounces_from_a_raw_doctype_form_route(self) -> None:
		self.assertEqual(NEXORA_HOME, resolve_redirect("/app/doctype/user", {"NEXORA Finance Manager"}))

	def test_bounces_from_a_raw_query_report_route(self) -> None:
		self.assertEqual(
			NEXORA_HOME, resolve_redirect("/app/query-report/general-ledger", {"NEXORA Auditor"})
		)


class TestEveryNexoraRoleReachesItsOwnScreens(unittest.TestCase):
	ALL_ACCESS_ROLES = (
		"System Manager",
		"NEXORA Administrator",
		"NEXORA Finance Manager",
		"NEXORA Finance Operator",
		"NEXORA Auditor",
		"NEXORA Project Viewer",
	)

	def test_each_role_reaches_a_nexora_page(self) -> None:
		for role in self.ALL_ACCESS_ROLES:
			with self.subTest(role=role):
				self.assertIsNone(resolve_redirect("/app/nexora-finance", {role}))

	def test_each_role_reaches_the_bare_app_root(self) -> None:
		for role in self.ALL_ACCESS_ROLES:
			with self.subTest(role=role):
				self.assertIsNone(resolve_redirect("/app", {role}))

	def test_reaches_the_bare_app_root_with_a_trailing_slash(self) -> None:
		self.assertIsNone(resolve_redirect("/app/", {"NEXORA Finance Manager"}))

	def test_landing_on_its_own_home_never_redirects_again(self) -> None:
		"""Si esto alguna vez devolviera un destino, la guarda de cliente entraría en
		un bucle infinito de redirecciones sobre su propio destino."""
		for role in self.ALL_ACCESS_ROLES:
			with self.subTest(role=role):
				self.assertIsNone(resolve_redirect(NEXORA_HOME, {role}))


class TestEveryNexoraRoleReachesRealNxrDoctypeLinks(unittest.TestCase):
	"""Varias pantallas ya enlazan de verdad a estos DocType vía
	`frappe.utils.get_form_link()` — bloquearlos habría sido una regresión real, no
	una guarda nueva. Válido para cualquier rol de NEXORA, `System Manager`/`NEXORA
	Administrator` incluidos: ya no hay excepción de rol, solo de ruta."""

	def test_reaches_an_nxr_contract_form(self) -> None:
		self.assertIsNone(resolve_redirect("/app/nxr-contract/CONTRACT-001", {"NEXORA Auditor"}))

	def test_reaches_an_nxr_operation_form(self) -> None:
		self.assertIsNone(resolve_redirect("/app/nxr-operation/OP-001", {"NEXORA Finance Operator"}))

	def test_reaches_an_nxr_fund_source_form(self) -> None:
		self.assertIsNone(resolve_redirect("/app/nxr-fund-source/FUND-001", {"NEXORA Finance Manager"}))

	def test_reaches_a_bare_nxr_doctype_list_too(self) -> None:
		self.assertIsNone(resolve_redirect("/app/nxr-contract", {"NEXORA Auditor"}))

	def test_system_manager_reaches_an_nxr_operation_form(self) -> None:
		self.assertIsNone(resolve_redirect("/app/nxr-operation/OP-001", {"System Manager"}))

	def test_nexora_administrator_reaches_an_nxr_contract_form(self) -> None:
		self.assertIsNone(resolve_redirect("/app/nxr-contract/CONTRACT-001", {"NEXORA Administrator"}))


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
