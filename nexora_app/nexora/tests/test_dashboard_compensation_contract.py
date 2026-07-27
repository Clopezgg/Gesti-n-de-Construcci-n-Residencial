from __future__ import annotations

import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestDashboardCompensationContract(unittest.TestCase):
	def test_dashboard_exposes_reversals_without_hiding_gross_income(self) -> None:
		code = (APP_ROOT / "nexora/page/nexora-dashboard/nexora-dashboard.js").read_text(
			encoding="utf-8"
		)
		for marker in (
			'"Compensated Total": __("Compensado total")',
			'const sourceTotals = analytics.source_totals || {}',
			'__("Anulado o reversado")',
			"sourceTotals.reversed_hnl",
			'__("Devoluciones reales")',
			"sourceTotals.returned_hnl",
			'__("Movimientos compensados")',
			"preservados en el Libro Central",
		):
			self.assertIn(marker, code)

	def test_dashboard_keeps_certified_identity_and_refresh_contract(self) -> None:
		code = (APP_ROOT / "nexora/page/nexora-dashboard/nexora-dashboard.js").read_text(
			encoding="utf-8"
		)
		for marker in (
			"const projectControl = page.add_field",
			"projectControl.get_value()",
			"Gestión Integral de Fondos, Proyectos y Operaciones",
			"nxr-project-name",
			"nxr-evidence-gallery",
			"nxr-contract-rows",
			'nexora:data-changed.nexora-dashboard',
		):
			self.assertIn(marker, code)


if __name__ == "__main__":
	unittest.main()
