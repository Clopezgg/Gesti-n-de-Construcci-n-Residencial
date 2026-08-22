from __future__ import annotations

import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestDashboardCompensationContract(unittest.TestCase):
	def test_dashboard_exposes_net_income_and_preserves_reversal_audit(self) -> None:
		"""AUDITORÍA VISUAL Y FUNCIONAL COMPLETA POST-DASHBOARD retiró la fila de seis
		métricas (`renderMetrics`, incluida la tarjeta "Fondos netos" que originalmente
		fijó este hallazgo) por duplicar tres de los cinco KPI reales de la
		reconstrucción visual definitiva. El ingreso neto real (después de reversos)
		no desapareció: se movió al servidor — `cashflow_query.monthly_cash_flow` ya
		usa `source_totals()["net_received_hnl"]` (nunca el bruto) para la serie
		"Ingresos" del gráfico de flujo de fondos — así que esta prueba verifica el
		mismo hallazgo real contra dónde vive ahora, en vez de una tarjeta que ya no
		existe."""
		code = (APP_ROOT / "nexora/page/nexora_dashboard/nexora_dashboard.js").read_text(encoding="utf-8")
		for marker in (
			'"Compensated Partial": __("Corregido parcialmente")',
			'"Compensated Total": __("Corregido totalmente")',
			"const sourceTotals = analytics.source_totals || {}",
			"sourceTotals.reversed_hnl",
			'__("Movimientos corregidos")',
			"anulaciones o reversos preservados en el historial financiero",
			"row.presentation_struck",
			"renderCashflowChart(data.cash_flow_monthly || [])",
		):
			self.assertIn(marker, code)
		self.assertNotIn('__("Anulado o reversado")', code)
		self.assertNotIn('__("Compensado total")', code)
		self.assertNotIn("function renderMetrics(", code)

		cashflow_query = (APP_ROOT / "dashboard/cashflow_query.py").read_text(encoding="utf-8")
		self.assertIn('"income_hnl": totals["net_received_hnl"]', cashflow_query)
		self.assertNotIn('totals["received_hnl"]', cashflow_query)

	def test_dashboard_keeps_certified_identity_and_refresh_contract(self) -> None:
		code = (APP_ROOT / "nexora/page/nexora_dashboard/nexora_dashboard.js").read_text(encoding="utf-8")
		for marker in (
			"const projectControl = page.add_field",
			"projectControl.get_value()",
			"Gestión Integral de Fondos, Proyectos y Operaciones",
			"nxr-project-name",
			"nxr-evidence-gallery",
			"nxr-contract-rows",
			"nexora:data-changed.nexora-dashboard",
		):
			self.assertIn(marker, code)


if __name__ == "__main__":
	unittest.main()
