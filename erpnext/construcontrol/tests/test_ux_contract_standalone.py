from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
UX = ROOT / "erpnext" / "public" / "js" / "construcontrol_ux.js"
CSS = ROOT / "erpnext" / "public" / "css" / "construcontrol_ux.css"
HOOKS = ROOT / "erpnext" / "hooks.py"


class UxContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ux = UX.read_text(encoding="utf-8")
        cls.css = CSS.read_text(encoding="utf-8")
        cls.hooks = HOOKS.read_text(encoding="utf-8")

    def test_all_forms_have_visible_exit_and_save_actions(self) -> None:
        for label in ("Cerrar", "Cancelar cambios", "Guardar", "Guardar y nuevo"):
            self.assertIn(label, self.ux)
        self.assertIn("cc-form-command-bar", self.css)
        self.assertIn("confirmDiscard", self.ux)

    def test_close_action_uses_current_route_not_stale_route(self) -> None:
        self.assertIn("goBackFromCurrent", self.ux)
        self.assertIn("event.stopImmediatePropagation()", self.ux)
        self.assertIn("frappe.get_route", self.ux)

    def test_modals_and_missing_routes_have_recovery(self) -> None:
        self.assertIn("cc-modal-close", self.ux)
        self.assertIn("Lamentablemente, no se puede encontrar", self.ux)
        self.assertIn("Volver al inicio", self.ux)
        self.assertIn("cc-route-recovery", self.css)

    def test_technical_errors_are_not_exposed_as_raw_tracebacks(self) -> None:
        self.assertIn("friendlyErrorMessage", self.ux)
        self.assertIn("Traceback", self.ux)
        self.assertIn("El error técnico quedó registrado", self.ux)
        self.assertIn("construcontrol_ux.js", self.hooks)


if __name__ == "__main__":
    unittest.main()
