from __future__ import annotations

import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestDashboardNetIncomeContract(unittest.TestCase):
	def test_dashboard_shows_net_income_without_reversal_metric_card(self) -> None:
		code = (APP_ROOT / "nexora/page/nexora-dashboard/nexora-dashboard.js").read_text(encoding="utf-8")
		self.assertIn('__("Ingresos netos")', code)
		self.assertIn("executive.net_received_hnl ?? executive.received_hnl", code)
		self.assertNotIn('__("Anulado o reversado")', code)

	def test_dashboard_preserves_compensation_alert_and_audit_link(self) -> None:
		code = (APP_ROOT / "nexora/page/nexora-dashboard/nexora-dashboard.js").read_text(encoding="utf-8")
		for marker in (
			"sourceTotals.reversed_hnl",
			'__("Movimientos compensados")',
			"preservados en el Libro Central",
			'"Compensated Total": __("Compensado total")',
		):
			self.assertIn(marker, code)

	def test_backend_deducts_only_reversals_linked_to_received_effects(self) -> None:
		code = (APP_ROOT / "dashboard/source_query.py").read_text(encoding="utf-8")
		for marker in (
			"reversed_effect.effect_type='Received'",
			"reversed_inflow_hnl",
			"gross_received_hnl",
			"net_received_hnl",
			"LEFT JOIN `tabNXR Operation Effect` reversed_effect",
		):
			self.assertIn(marker, code)
		self.assertNotIn(
			'net_received_amount(result["gross_received_hnl"], result["reversed_hnl"])',
			code,
		)


if __name__ == "__main__":
	unittest.main()
