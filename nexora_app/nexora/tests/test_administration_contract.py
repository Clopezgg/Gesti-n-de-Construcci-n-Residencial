"""Pruebas de contrato estático de `nexora.administration.service`.

Verifican estructura real de código sin ejecutar Frappe: que la cuenta
técnica `Administrator` queda excluida de toda lectura/escritura, que toda
función whitelisted exige un permiso server-side, que ninguna mutación de
rol o estado evita la comprobación de "último Administrador", y que cada
mutación queda auditada.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]


def function_body(source: str, name: str) -> str:
	match = re.search(rf"\ndef {re.escape(name)}\(.*?\n(?=\n@|\ndef |\Z)", source, flags=re.DOTALL)
	if not match:
		raise AssertionError(f"no se encontró la función {name!r}")
	return match.group(0)


def service_source() -> str:
	return (APP_ROOT / "administration/service.py").read_text(encoding="utf-8")


class TestEveryWhitelistedFunctionRequiresAnAction(unittest.TestCase):
	def test_every_whitelisted_function_requires_an_action(self) -> None:
		source = service_source()
		for name in (
			"list_users",
			"list_nexora_roles",
			"set_user_status",
			"set_user_roles",
			"list_recent_activity",
		):
			with self.subTest(function=name):
				body = function_body(source, name)
				self.assertIn("require_action(", body)

	def test_all_endpoints_are_whitelisted_post_only(self) -> None:
		source = service_source()
		for name in (
			"list_users",
			"list_nexora_roles",
			"set_user_status",
			"set_user_roles",
			"list_recent_activity",
		):
			with self.subTest(function=name):
				self.assertIn(f'@frappe.whitelist(methods=["POST"])\ndef {name}(', source)


class TestPermissionActionsAreDeclaredCorrectly(unittest.TestCase):
	def test_manage_and_view_actions_map_to_administrator_only(self) -> None:
		source = (APP_ROOT / "permissions.py").read_text(encoding="utf-8")
		block = source[
			source.index("ACTION_ROLES") : source.index("ACTION_ROLES")
			+ source[source.index("ACTION_ROLES") :].index("\n}")
		]
		self.assertIn('"manage_users": ADMINISTRATOR_ONLY_ROLES', block)
		self.assertIn('"view_users": ADMINISTRATOR_ONLY_ROLES', block)


class TestAdministratorAccountIsExcluded(unittest.TestCase):
	def test_the_technical_administrator_account_is_excluded_from_listing_and_mutation(self) -> None:
		source = service_source()
		self.assertIn('_EXCLUDED_ACCOUNTS = ("Administrator", "Guest")', source)
		self.assertIn("_require_existing_user", source)
		require_body = function_body(source, "_require_existing_user")
		self.assertIn("_EXCLUDED_ACCOUNTS", require_body)

	def test_set_user_status_and_set_user_roles_validate_the_target_user_exists_first(self) -> None:
		source = service_source()
		for name in ("set_user_status", "set_user_roles"):
			with self.subTest(function=name):
				body = function_body(source, name)
				self.assertIn("_require_existing_user(target_user)", body)


class TestLastAdministratorSafetyCheckIsWiredIntoBothMutations(unittest.TestCase):
	def test_set_user_status_checks_before_disabling(self) -> None:
		body = function_body(service_source(), "set_user_status")
		self.assertIn("assert_not_last_administrator(", body)
		check_at = body.index("assert_not_last_administrator(")
		save_at = body.index("doc.save(ignore_permissions=True)")
		self.assertLess(check_at, save_at)

	def test_set_user_roles_checks_before_saving_when_administrator_role_is_removed(self) -> None:
		body = function_body(service_source(), "set_user_roles")
		self.assertIn("assert_not_last_administrator(", body)
		self.assertIn("if ADMINISTRATOR_ROLE not in normalized_roles:", body)
		check_at = body.index("assert_not_last_administrator(")
		save_at = body.index("doc.save(ignore_permissions=True)")
		self.assertLess(check_at, save_at)

	def test_set_user_roles_never_touches_roles_outside_the_allowed_nexora_set(self) -> None:
		body = function_body(service_source(), "set_user_roles")
		self.assertIn("& ALLOWED_NEXORA_ROLES", body)


class TestEveryMutationIsAudited(unittest.TestCase):
	def test_set_user_status_and_set_user_roles_call_audit_after_saving(self) -> None:
		source = service_source()
		for name, event in (
			("set_user_status", "nexora_user_status_changed"),
			("set_user_roles", "nexora_user_roles_changed"),
		):
			with self.subTest(function=name):
				body = function_body(source, name)
				self.assertIn(f'"{event}"', body)
				save_at = body.index("doc.save(ignore_permissions=True)")
				audit_at = body.index("audit(")
				self.assertLess(save_at, audit_at)


if __name__ == "__main__":
	unittest.main()
