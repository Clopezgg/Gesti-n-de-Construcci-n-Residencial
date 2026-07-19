from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SERVICE = ROOT / "erpnext" / "construcontrol" / "construction.py"
SETUP = ROOT / "erpnext" / "construcontrol" / "construction_setup.py"
PAGE = ROOT / "erpnext" / "construcontrol" / "page" / "construcontrol_project_center" / "construcontrol_project_center.js"
INSTALL = ROOT / "erpnext" / "construcontrol" / "install.py"


class ConstructionContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = SERVICE.read_text(encoding="utf-8")
        cls.setup = SETUP.read_text(encoding="utf-8")
        cls.page = PAGE.read_text(encoding="utf-8")
        cls.install = INSTALL.read_text(encoding="utf-8")

    def test_project_control_consolidates_physical_and_financial_progress(self) -> None:
        for phrase in (
            "physical_progress_percent",
            "financial_progress_percent",
            "budget_variance_hnl",
            "committed_hnl",
            "actual_cost_hnl",
            "available_budget_hnl",
        ):
            self.assertIn(phrase, self.service)
            self.assertIn(phrase, self.setup)

    def test_project_service_does_not_delete_operational_records(self) -> None:
        self.assertNotIn("delete_doc", self.service)
        self.assertNotIn("DELETE FROM", self.service.upper())
        self.assertIn("recalculate_project_control", self.service)

    def test_project_center_integrates_core_construction_modules(self) -> None:
        for label in ("Fases de obra", "Contratos activos", "Materiales críticos", "Avances recientes"):
            self.assertIn(label, self.page)
        self.assertIn("construcontrol-project-center", self.install)

    def test_project_center_refresh_is_non_blocking_and_non_recursive(self) -> None:
        self.assertNotIn("frappe.dom.freeze", self.page)
        self.assertNotIn("frappe.dom.unfreeze", self.page)
        self.assertIn("syncingProjectField", self.page)
        self.assertIn("selectedProject === activeProject", self.page)
        self.assertIn("projectRequest", self.page)
        self.assertIn("setLoading(false)", self.page)


if __name__ == "__main__":
    unittest.main()
