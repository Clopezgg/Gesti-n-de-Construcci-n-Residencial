from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SHELL = ROOT / "erpnext" / "public" / "js" / "construcontrol_mobile.js"
CSS = ROOT / "erpnext" / "public" / "css" / "construcontrol_canonical.css"
HOOKS = ROOT / "erpnext" / "hooks.py"


class ConstruControlShellContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.shell = SHELL.read_text(encoding="utf-8")
        cls.css = CSS.read_text(encoding="utf-8")
        cls.hooks = HOOKS.read_text(encoding="utf-8")

    def test_shell_covers_desktop_mobile_and_close_navigation(self) -> None:
        required = (
            "cc-desktop-sidebar",
            "cc-app-topbar",
            "cc-mobile-nav",
            "cc-close-view",
            "construcontrol-dashboard",
            "construcontrol-profile",
            "construcontrol-users",
            'current[0] === "Form"',
        )
        for phrase in required:
            self.assertIn(phrase, self.shell)

    def test_shell_keeps_erpnext_as_hidden_engine(self) -> None:
        self.assertIn("body.cc-construcontrol-route > .navbar", self.css)
        self.assertIn("body.cc-construcontrol-route .desk-sidebar", self.css)
        self.assertIn("margin-left:var(--cc-sidebar)", self.css.replace(" ", ""))
        self.assertIn("construcontrol_canonical.css", self.hooks)

    def test_navigation_has_single_finance_and_work_control_model(self) -> None:
        expected = {
            "FI01": ("Ingresos", "CC Funding Source"),
            "FI02": ("Gastos", "CC Expense Control"),
            "FI03": ("Cuentas por pagar", "CC Payable Control"),
            "CO01": ("Contratos", "CC Labor Contract"),
            "PR01": ("Fases", "CC Construction Phase"),
            "MM01": ("Materiales", "CC Material Ledger"),
            "BI01": ("Reportes", "construcontrol-reporting-center"),
            "INT": ("Integraciones", "construcontrol-integrations"),
            "US01": ("Usuarios", "construcontrol-users"),
        }
        for code, values in expected.items():
            label, target = values
            self.assertEqual(self.shell.count(f'["{code}",'), 1)
            self.assertIn(f'"{label}"', self.shell)
            self.assertIn(f'"{target}"', self.shell)
        self.assertEqual(self.shell.count("Integraciones NEXT"), 0)
        self.assertEqual(self.shell.count("CC User Access"), 0)
        self.assertEqual(self.shell.count('["Workspace"'), 0)

    def test_obsolete_global_route_bridges_are_removed(self) -> None:
        obsolete = (
            ROOT / "erpnext" / "public" / "js" / "construcontrol_profile_bridge.js",
            ROOT / "erpnext" / "public" / "js" / "construcontrol_integrations_bridge.js",
        )
        for path in obsolete:
            self.assertFalse(path.exists(), f"Obsolete route bridge remains: {path.name}")
            self.assertNotIn(path.name, self.hooks)
        self.assertIn('go(["construcontrol-profile"])', self.shell)
        self.assertIn('["INT","Integraciones","⌘",["construcontrol-integrations"]', self.shell)

    def test_mobile_supports_safe_area_and_bottom_navigation(self) -> None:
        compact = re.sub(r"\s+", "", self.css)
        self.assertIn("safe-area-inset-bottom", self.css)
        self.assertIn("grid-template-columns:repeat(5", compact)
        self.assertIn("cc-more-sheet", self.css)
        self.assertIn("cc-more-backdrop", self.css)
        self.assertIn("Escape", self.shell)


if __name__ == "__main__":
    unittest.main()
