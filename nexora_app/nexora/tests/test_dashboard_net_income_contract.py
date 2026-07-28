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

	def test_dashboard_uses_financial_business_colors(self) -> None:
		code = (APP_ROOT / "nexora/page/nexora-dashboard/nexora-dashboard.js").read_text(encoding="utf-8")
		for marker in (
			'{ label: __("Ingresos netos"), value: executive.net_received_hnl ?? executive.received_hnl, tone: "income" }',
			'{ label: __("Gastos ejecutados"), value: executive.spent_hnl, tone: "expense" }',
			'{ label: __("Caja disponible"), value: finance.total_available_hnl ?? executive.cash_available_hnl, tone: "balance" }',
			'income: "var(--green-600, #218838)"',
			'expense: "var(--red-600, #c82333)"',
			'balance: "var(--blue-600, #0d6efd)"',
			'renderBars(".nxr-expense-bars", analytics.expenses_by_category || [], (row) => row.label, "expense")',
			'renderBars(".nxr-income-bars", analytics.income_by_channel || [], (row) => channelLabels[row.label] || row.label, "income")',
		):
			self.assertIn(marker, code)

	def test_recent_operations_use_business_labels_and_strike_voided_amounts(self) -> None:
		code = (APP_ROOT / "nexora/page/nexora-dashboard/nexora-dashboard.js").read_text(encoding="utf-8")
		for marker in (
			'Cancellation: __("Anulado")',
			'Posted: __("Contabilizado")',
			'Remittance: __("Remesa")',
			'Deposit: __("Depósito")',
			'Transfer: __("Transferencia")',
			'Cash: __("Efectivo")',
			"row.presentation_struck ? `<s>${content}</s>` : content",
			"presentationLabels[kind] || operationLabels[row.operation_type] || row.operation_type",
			'kind === "Income" && row.source_channel',
		):
			self.assertIn(marker, code)

	def test_backend_exposes_bounded_ledger_presentation_metadata(self) -> None:
		code = (APP_ROOT / "dashboard/operational_query.py").read_text(encoding="utf-8")
		for marker in (
			"_operation_source_channels",
			"RECENT_OPERATION_LIMIT * 20",
			'operation_type == "Analytic Adjustment" and bool(row.get("reversal_of"))',
			'"presentation_kind": kind',
			'"presentation_status": "Posted"',
			'"presentation_tone": tone',
			'"presentation_struck": is_voided',
			'"source_channel": channels[0] if channels else None',
			'"status": ["!=", "Draft"]',
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
