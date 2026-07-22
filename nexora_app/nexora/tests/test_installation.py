from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.install import BASE_ROLES


class TestNexoraInstallation(FrappeTestCase):
    def test_app_and_minimum_fixtures_are_installed(self) -> None:
        self.assertIn("nexora", frappe.get_installed_apps())
        self.assertIn("erpnext", frappe.get_installed_apps())
        for role_name in BASE_ROLES:
            self.assertTrue(frappe.db.exists("Role", role_name))
        self.assertTrue(frappe.db.exists("Workspace", "NEXORA"))

    def test_workspace_contains_only_nexora_identity(self) -> None:
        workspace = frappe.get_doc("Workspace", "NEXORA")
        serialized = workspace.as_json()
        self.assertIn("NEXORA", serialized)
        self.assertNotIn("ConstruControl", serialized)
