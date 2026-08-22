from __future__ import annotations

import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestDashboardNetIncomeContract(unittest.TestCase):
	def test_dashboard_shows_net_income_without_reversal_metric_card(self) -> None:
		"""AUDITORÍA VISUAL Y FUNCIONAL COMPLETA POST-DASHBOARD retiró la tarjeta
		"Fondos netos" (parte de `renderMetrics`, ya eliminada por duplicar KPI reales
		de la reconstrucción visual definitiva) — el ingreso neto real (después de
		reversos, nunca el bruto) sigue existiendo, ahora en el servidor:
		`cashflow_query.monthly_cash_flow` calcula la serie "Ingresos" del gráfico de
		flujo de fondos con `source_totals()["net_received_hnl"]`."""
		code = (APP_ROOT / "nexora/page/nexora_dashboard/nexora_dashboard.js").read_text(encoding="utf-8")
		self.assertNotIn('__("Fondos netos")', code)
		self.assertNotIn('__("Anulado o reversado")', code)
		cashflow_query = (APP_ROOT / "dashboard/cashflow_query.py").read_text(encoding="utf-8")
		self.assertIn('"income_hnl": totals["net_received_hnl"]', cashflow_query)

	def test_dashboard_preserves_correction_alert_and_audit_link(self) -> None:
		code = (APP_ROOT / "nexora/page/nexora_dashboard/nexora_dashboard.js").read_text(encoding="utf-8")
		for marker in (
			"sourceTotals.reversed_hnl",
			'__("Movimientos corregidos")',
			"anulaciones o reversos preservados en el historial financiero",
			'"Compensated Partial": __("Corregido parcialmente")',
			'"Compensated Total": __("Corregido totalmente")',
		):
			self.assertIn(marker, code)

	def test_dashboard_uses_financial_business_colors(self) -> None:
		"""AUDITORÍA VISUAL Y FUNCIONAL COMPLETA POST-DASHBOARD: los ejemplos
		originales vivían en `renderMetrics` (ya retirada); la fila real de KPI
		(`renderKpiRow`) es ahora el punto real donde `tone` decide el color, con los
		mismos tres tonos de negocio."""
		code = (APP_ROOT / "nexora/page/nexora_dashboard/nexora_dashboard.js").read_text(encoding="utf-8")
		for marker in (
			'label: __("Saldo disponible")',
			"value: executive.cash_available_hnl",
			'tone: "balance"',
			'label: __("Pendiente de pagar")',
			"value: executive.pending_obligations_hnl",
			'tone: "expense"',
		):
			self.assertIn(marker, code)
		# NXR-UX-0013: tokens del Design System, no colores propios de esta pantalla con
		# respaldo hexadecimal de Bootstrap. `--nxr-money-out` (gasto) es tinta neutra a
		# propósito, no rojo — pintar de rojo cada gasto legítimo entrena a ignorar el
		# rojo, y entonces deja de servir para avisar de lo que sí está mal (ver el
		# comentario de esa misma decisión en nexora_design_system.css).
		self.assertIn('income: "var(--nxr-money-in)"', code)
		self.assertIn('expense: "var(--nxr-money-out)"', code)
		self.assertIn('balance: "var(--nxr-accent)"', code)
		self.assertNotIn("var(--green-600", code)
		self.assertNotIn("var(--red-600", code)
		self.assertNotIn("var(--blue-600", code)

	def test_recent_operations_use_human_labels_and_strike_voided_amounts(self) -> None:
		code = (APP_ROOT / "nexora/page/nexora_dashboard/nexora_dashboard.js").read_text(encoding="utf-8")
		for marker in (
			'Cancellation: __("Anulado")',
			'Posted: __("Registrado definitivamente")',
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
