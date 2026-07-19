from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SERVICE = ROOT / "erpnext" / "construcontrol" / "users.py"
PAGE = ROOT / "erpnext" / "construcontrol" / "page" / "construcontrol_users" / "construcontrol_users.js"
MOBILE = ROOT / "erpnext" / "public" / "js" / "construcontrol_mobile.js"
INSTALL = ROOT / "erpnext" / "construcontrol" / "install.py"
SPECIALIZATION = ROOT / "erpnext" / "construcontrol" / "schema_specialization.py"


def load_service(roles: list[str]):
    fake = types.ModuleType("frappe")
    fake._ = lambda value: value
    fake.PermissionError = PermissionError
    fake.get_roles = lambda: roles
    fake.throw = lambda message, *_args: (_ for _ in ()).throw(ValueError(message))
    fake.session = types.SimpleNamespace(user="manager@example.com")
    fake.db = types.SimpleNamespace(exists=lambda *_args, **_kwargs: False)
    fake.whitelist = lambda *args, **kwargs: (lambda fn: fn) if args == () else args[0]

    utils = types.ModuleType("frappe.utils")
    utils.cint = lambda value: int(value or 0)
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
        cls.page = PAGE.read_text(encoding="utf-8")
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
        module.frappe.db.exists = lambda doctype, filters=None: doctype == "Has Role" and filters.get("role") == "System Manager"
        with self.assertRaisesRegex(ValueError, "otra cuenta ADMIN"):
            module._require_target_management("admin2@example.com")

    def test_system_manager_can_modify_existing_admin_account(self) -> None:
        module = load_service(["System Manager"])
        module.frappe.db.exists = lambda doctype, filters=None: doctype == "Has Role" and filters.get("role") == "System Manager"
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


if __name__ == "__main__":
    unittest.main()
