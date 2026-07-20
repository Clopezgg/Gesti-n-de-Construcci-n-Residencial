from __future__ import annotations

import ast
import unittest
from pathlib import Path

RUNTIME_SMOKE = Path(__file__).with_name("runtime_smoke.py")
USER_CONTEXT = Path(__file__).with_name("test_runtime_user_context.py")
HOOKS = Path(__file__).resolve().parents[2] / "hooks.py"
INSTALL = Path(__file__).resolve().parents[1] / "install.py"
INSTALL_ENTRYPOINT = Path(__file__).resolve().parents[1] / "install_entrypoint.py"


class RuntimeSmokeContractTest(unittest.TestCase):
    def test_project_fixtures_include_a_real_company(self) -> None:
        source = RUNTIME_SMOKE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        project_payloads = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            values = {
                key.value: value
                for key, value in zip(node.keys, node.values, strict=False)
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
            if isinstance(values.get("doctype"), ast.Constant) and values["doctype"].value == "Project":
                project_payloads.append(values)

        self.assertEqual(len(project_payloads), 3)
        for payload in project_payloads:
            self.assertIn("company", payload)
            self.assertIsInstance(payload["company"], ast.Name)
            self.assertEqual(payload["company"].id, "company")

    def test_company_fixture_uses_required_stock_fixture_honduras_and_hnl(self) -> None:
        source = RUNTIME_SMOKE.read_text(encoding="utf-8")
        self.assertIn('frappe.db.exists("Warehouse Type", "Transit")', source)
        self.assertIn('{"doctype": "Warehouse Type", "name": "Transit"}', source)
        self.assertIn('"country": "Honduras"', source)
        self.assertIn('"default_currency": "HNL"', source)

    def test_runtime_user_switching_is_scoped_and_test_only(self) -> None:
        runtime_source = RUNTIME_SMOKE.read_text(encoding="utf-8")
        helper_source = USER_CONTEXT.read_text(encoding="utf-8")
        self.assertNotIn("frappe.set_user(", runtime_source)
        self.assertIn("with runtime_user(", runtime_source)
        self.assertIn("@contextmanager", helper_source)
        self.assertIn("finally:", helper_source)
        self.assertIn("frappe.set_user(previous", helper_source)

    def test_paid_runtime_expense_has_required_evidence(self) -> None:
        runtime_source = RUNTIME_SMOKE.read_text(encoding="utf-8")
        self.assertIn('"payment_status": "paid"', runtime_source)
        self.assertIn('"payment_reference": f"CI-PAY-{marker}"', runtime_source)
        self.assertIn('"payment_evidence": f"/private/files/CI-PAY-{marker}.txt"', runtime_source)

    def test_full_runtime_installer_runs_after_install_and_migrate(self) -> None:
        hooks_source = HOOKS.read_text(encoding="utf-8")
        install_source = INSTALL.read_text(encoding="utf-8")
        entrypoint_source = INSTALL_ENTRYPOINT.read_text(encoding="utf-8")
        self.assertIn(
            'after_install = "erpnext.construcontrol.install_entrypoint.after_install"',
            hooks_source,
        )
        self.assertIn('"erpnext.construcontrol.install.after_migrate"', hooks_source)
        self.assertIn("erpnext.setup.install import after_install", entrypoint_source)
        self.assertIn("erpnext_after_install()", entrypoint_source)
        self.assertIn("after_migrate()", entrypoint_source)
        for page in (
            "construcontrol-dashboard",
            "construcontrol-profile",
            "construcontrol-project-center",
            "construcontrol-users",
            "construcontrol-integrations",
            "construcontrol-reporting-center",
            "construcontrol-closing-center",
            "construcontrol-migration-console",
        ):
            self.assertIn(f'"{page}"', install_source)
        self.assertNotIn('"construcontrol-weekly-closing"', install_source)
        self.assertIn("ensure_canonical_pages", install_source)
        self.assertIn("_validate_runtime_pages()", install_source)


if __name__ == "__main__":
    unittest.main()
