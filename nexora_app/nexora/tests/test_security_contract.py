from __future__ import annotations

import json
import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestSecurityContract(unittest.TestCase):
	def test_fixture_role_exists(self) -> None:
		path = APP_ROOT / "fixtures/role.json"
		self.assertTrue(path.is_file())

	def test_fixture_has_correct_roles(self) -> None:
		path = APP_ROOT / "fixtures/role.json"
		roles = json.loads(path.read_text(encoding="utf-8"))
		role_names = {r["role_name"] for r in roles}
		expected = {
			"NEXORA Administrator",
			"NEXORA Finance Manager",
			"NEXORA Finance Operator",
			"NEXORA Auditor",
			"NEXORA Project Viewer",
		}
		self.assertEqual(expected, role_names)

	def test_fixture_roles_have_desk_access(self) -> None:
		path = APP_ROOT / "fixtures/role.json"
		roles = json.loads(path.read_text(encoding="utf-8"))
		for role in roles:
			self.assertEqual(1, role["desk_access"], f"{role['role_name']} debe tener desk_access")

	def test_permissions_module_uses_same_roles(self) -> None:
		path = APP_ROOT / "fixtures/role.json"
		roles = json.loads(path.read_text(encoding="utf-8"))
		role_names = {r["role_name"] for r in roles}
		expected = {
			"NEXORA Administrator",
			"NEXORA Finance Manager",
			"NEXORA Finance Operator",
			"NEXORA Auditor",
			"NEXORA Project Viewer",
		}
		for role in expected:
			self.assertIn(role, role_names, f"{role} debe estar en fixtures/role.json")
