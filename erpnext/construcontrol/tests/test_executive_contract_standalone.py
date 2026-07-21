from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SERVICE = ROOT / "erpnext" / "construcontrol" / "executive.py"
IMPLEMENTATION = ROOT / "erpnext" / "construcontrol" / "executive_impl.py"
DASHBOARD = (
	ROOT / "erpnext" / "construcontrol" / "page" / "construcontrol_dashboard" / "construcontrol_dashboard.js"
)
REPORTS = ROOT / "erpnext" / "construcontrol" / "executive_reports.py"
INSTALL = ROOT / "erpnext" / "construcontrol" / "install.py"


class ExecutiveContractTest(unittest.TestCase):
	@classmethod
	def setUpClass(cls) -> None:
		cls.public_service = SERVICE.read_text(encoding="utf-8")
		cls.implementation = IMPLEMENTATION.read_text(encoding="utf-8")
		cls.service = cls.public_service + "\n" + cls.implementation
		cls.dashboard = DASHBOARD.read_text(encoding="utf-8")
		cls.reports = REPORTS.read_text(encoding="utf-8")
		cls.install = INSTALL.read_text(encoding="utf-8")

	def test_dashboard_contains_complete_financial_and_physical_summary(self) -> None:
		for field in (
			"received_hnl",
			"expense_total_hnl",
			"paid_hnl",
			"cash_available_hnl",
			"payable_balance_hnl",
			"updated_budget_hnl",
			"committed_hnl",
			"available_budget_hnl",
			"physical_percent",
			"financial_percent",
		):
			self.assertIn(field, self.service)

	def test_dashboard_exposes_localized_actionable_alerts(self) -> None:
		for phrase in (
			"Cuentas vencidas",
			"Inventario crítico",
			"Ingresos sin conciliar",
			"Fases atrasadas",
		):
			self.assertIn(phrase, self.service)
		self.assertIn('"route": [', self.service)
		self.assertIn('"schedule_status_label"', self.service)
		self.assertIn("row.action_label", self.dashboard)
		self.assertIn("row.record_type_label", self.dashboard)
		self.assertIn("alert?.route", self.dashboard)

	def test_dashboard_is_compact_and_does_not_duplicate_navigation(self) -> None:
		for label in (
			"Gastos por categoría",
			"Ingresos por canal",
			"Cuentas por pagar",
			"Inventario crítico",
			"Actividad reciente",
		):
			self.assertIn(label, self.dashboard)
		self.assertIn("slice(0, 3)", self.dashboard)
		self.assertIn("alerts[:4]", self.public_service)
		self.assertNotIn("Módulos ConstruControl", self.dashboard)
		self.assertNotIn("cc-module-grid", self.dashboard)

	def test_dashboard_refresh_cannot_freeze_or_recurse_forever(self) -> None:
		self.assertNotIn("frappe.dom.freeze", self.dashboard)
		self.assertNotIn("frappe.dom.unfreeze", self.dashboard)
		self.assertIn("syncingProjectField", self.dashboard)
		self.assertIn("selectedProject === activeProject", self.dashboard)
		self.assertIn("requestId !== dashboardRequest", self.dashboard)
		self.assertIn("cc-dashboard-refresh-state", self.dashboard)
		self.assertIn(".finally(() =>", self.dashboard)

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
