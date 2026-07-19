from __future__ import annotations

import importlib.util
import json
import sys
import types
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SERVICE = ROOT / "erpnext" / "construcontrol" / "users.py"
PROFILE = ROOT / "erpnext" / "construcontrol" / "profile.py"
PAGE = ROOT / "erpnext" / "construcontrol" / "page" / "construcontrol_users" / "construcontrol_users.js"
ASSETS = ROOT / "erpnext" / "construcontrol" / "runtime" / "assets.json"
MOBILE = ROOT / "erpnext" / "public" / "js" / "construcontrol_mobile.js"
INSTALL = ROOT / "erpnext" / "construcontrol" / "install.py"
SPECIALIZATION = ROOT / "erpnext" / "construcontrol" / "schema_specialization.py"


def load_service(roles: list[str]):
	fake = types.ModuleType("frappe")
	fake._ = lambda value: value
	fake.PermissionError = PermissionError
	fake.get_roles = lambda user=None: roles
	fake.get_all = lambda *_args, **_kwargs: []
	fake.throw = lambda message, *_args: (_ for _ in ()).throw(ValueError(message))
	fake.session = types.SimpleNamespace(user="manager@example.com")
	fake.db = types.SimpleNamespace(
		exists=lambda *_args, **_kwargs: False,
		get_value=lambda *_args, **_kwargs: None,
	)
	fake.whitelist = lambda *args, **kwargs: (lambda fn: fn) if args == () else args[0]

	utils = types.ModuleType("frappe.utils")
	utils.cint = lambda value: int(value or 0)
	utils.now_datetime = datetime.now
	utils.today = lambda: "2026-07-19"
	utils.validate_email_address = lambda value, throw=False: "@" in str(value)
	fake.utils = utils
	sys.modules["frappe"] = fake
	sys.modules["frappe.utils"] = utils

	name = "cc_users_test_module"
	spec = importlib.util.spec_from_file_location(name, SERVICE)
	module = importlib.util.module_from_spec(spec)
	assert spec and spec.loader
	spec.loader.exec_module(module)
	return module


class UsersContractTest(unittest.TestCase):
	@classmethod
	def setUpClass(cls) -> None:
		cls.service = SERVICE.read_text(encoding="utf-8")
		cls.profile = PROFILE.read_text(encoding="utf-8")
		cls.page = PAGE.read_text(encoding="utf-8")
		cls.assets = json.loads(ASSETS.read_text(encoding="utf-8"))
		cls.mobile = MOBILE.read_text(encoding="utf-8")
		cls.install = INSTALL.read_text(encoding="utf-8")
		cls.specialization = SPECIALIZATION.read_text(encoding="utf-8")

	def test_role_labels_are_resolved_by_backend_rules(self) -> None:
		module = load_service(["System Manager"])
		self.assertEqual(module._visible_role({"System Manager", "ConstruControl Viewer"}), "ADMIN")
		self.assertEqual(module._visible_role({"ConstruControl Operator"}), "OPERATOR")
		self.assertEqual(module._role_from_label("viewer"), "ConstruControl Viewer")
		self.assertEqual(module._role_from_label("admin"), "System Manager")

	def test_non_admin_cannot_assign_system_manager(self) -> None:
		module = load_service(["ConstruControl Manager"])
		with self.assertRaisesRegex(ValueError, "Solo un administrador"):
			module._role_from_label("ADMIN")

	def test_non_admin_cannot_modify_existing_admin_account(self) -> None:
		module = load_service(["ConstruControl Manager"])
		module.frappe.db.exists = (
			lambda doctype, filters=None: doctype == "Has Role" and filters.get("role") == "System Manager"
		)
		with self.assertRaisesRegex(ValueError, "cuenta ADMIN"):
			module._require_target_management("admin2@example.com")

	def test_system_manager_can_modify_existing_admin_account(self) -> None:
		module = load_service(["System Manager"])
		module.frappe.db.exists = (
			lambda doctype, filters=None: doctype == "Has Role" and filters.get("role") == "System Manager"
		)
		module._require_target_management("admin2@example.com")

	def test_official_users_center_uses_native_users_and_backend_authorization(self) -> None:
		self.assertIn('"User"', self.service)
		self.assertIn('"Has Role"', self.service)
		self.assertIn('"User Permission"', self.service)
		self.assertIn("_require_management()", self.service)
		self.assertIn("_require_target_management", self.service)
		self.assertIn("No tiene permisos para administrar usuarios", self.service)
		self.assertNotIn('frappe.set_route("List", "CC User Access")', self.page)

	def test_historical_access_is_not_the_official_users_module(self) -> None:
		self.assertIn('"construcontrol-users"', self.mobile)
		self.assertNotIn('["List","CC User Access"]', self.mobile.replace(" ", ""))
		self.assertIn('"construcontrol-users"', self.install)
		self.assertIn('"CC User Access"', self.specialization)
		self.assertIn('"hidden": 1', self.specialization)
		self.assertIn("Los registros históricos", self.page)

	def test_user_page_supports_create_edit_suspend_and_project_assignment(self) -> None:
		for phrase in (
			"Nuevo usuario",
			"save_user",
			"set_user_enabled",
			"Proyecto principal",
			"Suspender",
			"Reactivar",
		):
			self.assertIn(phrase, self.page)

	def test_limited_roles_require_project_scope(self) -> None:
		module = load_service(["System Manager"])
		for role in (
			"ConstruControl Operator",
			"ConstruControl Auditor",
			"ConstruControl Viewer",
		):
			with self.subTest(role=role), self.assertRaisesRegex(ValueError, "Asigne un proyecto"):
				module._validate_project_assignment(role, "")
		self.assertEqual(module._validate_project_assignment("ConstruControl Manager", ""), "")

	def test_administrator_and_last_admin_transitions_are_blocked(self) -> None:
		module = load_service(["System Manager"])
		module.frappe.db.exists = lambda doctype, filters=None: (
			doctype == "Has Role" and filters and filters.get("role") == "System Manager"
		)
		with self.assertRaisesRegex(ValueError, "Administrator no puede"):
			module._assert_admin_transition(
				"Administrator",
				new_role="ConstruControl Manager",
				enabled=1,
			)
		module.frappe.session.user = "root@example.com"
		module._enabled_system_managers = lambda **_kwargs: []
		with self.assertRaisesRegex(ValueError, "última cuenta ADMIN"):
			module._assert_admin_transition(
				"admin2@example.com",
				new_role="ConstruControl Manager",
				enabled=1,
			)

	def test_backend_lifecycle_endpoints_are_post_only_and_audited(self) -> None:
		for endpoint in ("save_user", "approve_user", "set_user_enabled", "delete_user"):
			self.assertIn(f"def {endpoint}", self.service)
		self.assertGreaterEqual(self.service.count('@frappe.whitelist(methods=["POST"])'), 4)
		for action in ("CREATE", "UPDATE", "APPROVE", "SUSPEND", "REACTIVATE", "DELETE"):
			self.assertIn(action, self.service)
		self.assertIn('"actor_role"', self.service)
		self.assertIn('"actor_user_id"', self.service)
		self.assertIn('"record_type": "User"', self.service)

	def test_profile_and_direct_page_access_use_real_roles(self) -> None:
		self.assertIn('"role": _visible_business_role()', self.profile)
		self.assertNotIn('"role": user', self.profile)
		users_page = next(row for row in self.assets["pages"] if row["name"] == "construcontrol-users")
		self.assertEqual(
			users_page["roles"],
			["System Manager", "ConstruControl Manager"],
		)


if __name__ == "__main__":
	unittest.main()
