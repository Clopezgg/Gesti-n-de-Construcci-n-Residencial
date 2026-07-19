from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SHELL = ROOT / "erpnext" / "public" / "js" / "construcontrol_mobile.js"
CSS = ROOT / "erpnext" / "public" / "css" / "construcontrol.css"


class ConstruControlShellContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.shell = SHELL.read_text(encoding="utf-8")
        cls.css = CSS.read_text(encoding="utf-8")

    def test_shell_covers_desktop_mobile_and_close_navigation(self) -> None:
        for phrase in (
            "cc-desktop-sidebar",
            "cc-app-topbar",
            "cc-mobile-nav",
            "cc-close-view",
            "ensureCloseAction",
            "construcontrol-dashboard",
        ):
            self.assertIn(phrase, self.shell)

    def test_shell_keeps_erpnext_as_hidden_engine(self) -> None:
        self.assertIn("body.cc-construcontrol-route > .navbar", self.css)
        self.assertIn("body.cc-construcontrol-route .desk-sidebar", self.css)
        self.assertIn("margin-left: var(--cc-sidebar-width)", self.css)

    def test_navigation_has_single_finance_and_work_control_model(self) -> None:
        for label in (
            'label: "Ingresos"',
            'label: "Gastos"',
            'label: "Contratos"',
            'label: "Fases"',
            'label: "Materiales"',
            'label: "Reportes"',
            'label: "Integraciones"',
        ):
            self.assertIn(label, self.shell)

    def test_mobile_supports_safe_area_and_bottom_navigation(self) -> None:
        self.assertIn("safe-area-inset-bottom", self.css)
        self.assertIn("grid-template-columns: repeat(5", self.css)
        self.assertIn("cc-more-sheet", self.css)


if __name__ == "__main__":
    unittest.main()
