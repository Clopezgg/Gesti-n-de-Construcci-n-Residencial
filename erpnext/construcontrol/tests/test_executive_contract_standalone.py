from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SERVICE = ROOT / "erpnext" / "construcontrol" / "executive.py"
DASHBOARD = ROOT / "erpnext" / "construcontrol" / "page" / "construcontrol_dashboard" / "construcontrol_dashboard.js"
REPORTS = ROOT / "erpnext" / "construcontrol" / "executive_reports.py"
INSTALL = ROOT / "erpnext" / "construcontrol" / "install.py"


class ExecutiveContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = SERVICE.read_text(encoding="utf-8")
        cls.dashboard = DASHBOARD.read_text(encoding="utf-8")
        cls.reports = REPORTS.read_text(encoding="utf-8")
        cls.install = INSTALL.read_text(encoding="utf-8")

    def test_dashboard_contains_complete_financial_and_physical_summary(self) -> None:
        for field in (
            "received_hnl",
            "spent_hnl",
            "cash_available_hnl",
            "payable_balance_hnl",
            "updated_budget_hnl",
            "committed_hnl",
            "available_budget_hnl",
            "physical_percent",
            "financial_percent",
        ):
            self.assertIn(field, self.service)

    def test_dashboard_exposes_alerts_and_operational_drilldown(self) -> None:
        for phrase in (
            "Cuentas vencidas",
            "Materiales críticos",
            "Ingresos sin conciliar",
            "Fases atrasadas",
        ):
            self.assertIn(phrase, self.service)
        for label in (
            "Gastos por categoría",
            "Ingresos por canal",
            "Cuentas por pagar",
            "Inventario crítico",
            "Actividad reciente",
        ):
            self.assertIn(label, self.dashboard)

    def test_executive_reports_are_installed_idempotently(self) -> None:
        for report in (
            "FI03 Cuentas por Pagar",
            "PR02 Presupuesto vs Ejecución",
            "PR03 Fases y Desviaciones",
            "MM03 Inventario Crítico",
            "FI04 Ingresos y Conciliación",
        ):
            self.assertIn(report, self.reports)
        self.assertIn("ensure_executive_reports()", self.install)


if __name__ == "__main__":
    unittest.main()
