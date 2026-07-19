from __future__ import annotations

import importlib.util
import inspect
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SERVICE = ROOT / "erpnext" / "construcontrol" / "access.py"
HOOKS = ROOT / "erpnext" / "hooks.py"


def load_access(roles: list[str], permissions: list[str] | None = None):
    permissions = permissions or []
    fake = types.ModuleType("frappe")
    fake._ = lambda value: value
    fake.PermissionError = PermissionError
    fake.get_roles = lambda: roles
    fake.session = types.SimpleNamespace(user="user@example.com")
    fake.flags = types.SimpleNamespace()
    fake.throw = lambda message, *_args: (_ for _ in ()).throw(ValueError(message))
    fake.get_all = lambda doctype, **kwargs: list(permissions) if doctype == "User Permission" else []
    fake.db = types.SimpleNamespace(exists=lambda doctype, name: doctype == "Project" and name in {"P1", "P2"})
    sys.modules["frappe"] = fake

    spec = importlib.util.spec_from_file_location("cc_access_test_module", SERVICE)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class AccessContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.hooks = HOOKS.read_text(encoding="utf-8")

    def test_manager_has_global_project_access(self) -> None:
        module = load_access(["ConstruControl Manager"])
        self.assertIsNone(module.allowed_project_names())
        self.assertEqual(module.project_filter(), {})

    def test_operator_is_limited_to_explicit_project_permissions(self) -> None:
        module = load_access(["ConstruControl Operator"], ["P1"])
        self.assertEqual(module.allowed_project_names(), ["P1"])
        self.assertEqual(module.assert_project_access("P1"), "P1")
        with self.assertRaisesRegex(ValueError, "No tiene permiso"):
            module.assert_project_access("P2")

    def test_unassigned_limited_user_cannot_fall_back_to_all_projects(self) -> None:
        module = load_access(["ConstruControl Viewer"])
        self.assertEqual(module.project_filter(), {"project": "__construcontrol_no_project_access__"})

    def test_viewer_cannot_execute_write_operation(self) -> None:
        module = load_access(["ConstruControl Viewer"], ["P1"])
        with self.assertRaisesRegex(ValueError, "No tiene permisos"):
            module.assert_project_access("P1", write=True)

    def test_document_validator_accepts_frappe_event_method_argument(self) -> None:
        module = load_access(["ConstruControl Operator"], ["P1"])
        parameters = inspect.signature(module.validate_document_project_access).parameters
        self.assertIn("method", parameters)
        fake_doc = types.SimpleNamespace(
            meta=types.SimpleNamespace(has_field=lambda fieldname: fieldname == "project"),
            get=lambda fieldname: "P1" if fieldname == "project" else None,
        )
        module.validate_document_project_access(fake_doc, "validate")

    def test_every_visible_project_module_has_backend_write_guard(self) -> None:
        for doctype in (
            "CC Payable Control",
            "CC Construction Phase",
            "CC Procurement Request",
            "CC Progress Update",
            "CC Weekly Closing",
            "CC Project Profile",
            "CC Generated Report",
        ):
            self.assertIn(f'"{doctype}"', self.hooks)
        self.assertIn("erpnext.construcontrol.access.validate_document_project_access", self.hooks)


if __name__ == "__main__":
    unittest.main()
