from __future__ import annotations

import pathlib
import unittest

PACKAGE = pathlib.Path(__file__).resolve().parents[1]
DESIGN_SYSTEM = PACKAGE / "public/css/nexora_design_system.css"
OPERATIONAL_CSS = PACKAGE / "public/css/nexora_operational.css"
DASHBOARD = PACKAGE / "nexora/page/nexora_dashboard/nexora_dashboard.js"
CONTRACTS = PACKAGE / "nexora/page/nexora_contracts/nexora_contracts.js"


class TestMoneyBreakdownDesignSystemContract(unittest.TestCase):
	"""NXR-UX-0013 — números explicables.

	Presupuesto, comprometido, ejecutado, pagado, disponible, retenido y pendiente no
	son el mismo número con nombre distinto. Estas pruebas verifican el componente
	`.nxr-ds-money-row` (nuevo, Capítulo 26 del Design System) y que use los tokens de
	dinero ya existentes (`--nxr-money-in/out/void`), no colores propios por pantalla.
	"""

	def source(self) -> str:
		return DESIGN_SYSTEM.read_text(encoding="utf-8")

	def test_money_row_component_exists_with_four_tones(self) -> None:
		code = self.source()
		for selector in (
			".nxr-ds-money-list",
			".nxr-ds-money-row",
			".nxr-ds-money-row__label",
			".nxr-ds-money-row__value",
			".nxr-ds-money-row--reference",
			".nxr-ds-money-row--pending",
			".nxr-ds-money-row--spent",
			".nxr-ds-money-row--available",
		):
			self.assertIn(selector, code)

	def test_money_row_tones_reuse_existing_design_tokens_not_new_colors(self) -> None:
		"""No es un séptimo color por concepto: cuatro tonos existentes agrupan los siete
		conceptos financieros (referencia/pendiente/gastado/disponible)."""
		code = self.source()
		block = code.split(".nxr-ds-money-row--reference", 1)[1]
		self.assertIn("var(--nxr-text-primary)", block)
		self.assertIn("var(--nxr-warning)", block)
		self.assertIn("var(--nxr-money-out)", block)
		self.assertIn("var(--nxr-money-in)", block)

	def test_money_row_never_touches_a_bare_element(self) -> None:
		"""Se carga en todo el escritorio de Frappe (mismo criterio que
		test_design_system_contract.py): las reglas nuevas deben ir sobre clases, no
		sobre selectores de elemento crudos que pintarían fuera de NEXORA."""
		code = self.source()
		block_start = code.index("/* Desglose de dinero")
		block_end = code.index("/* Distintivos")
		block = code[block_start:block_end]
		for bare in ("\ndiv {", "\nspan {", "\np {"):
			self.assertNotIn(bare, block)


class TestDashboardFinancialToneContract(unittest.TestCase):
	def source(self) -> str:
		return DASHBOARD.read_text(encoding="utf-8")

	def test_dashboard_tones_use_design_system_tokens(self) -> None:
		code = self.source()
		self.assertIn('income: "var(--nxr-money-in)"', code)
		self.assertIn('expense: "var(--nxr-money-out)"', code)
		self.assertIn('balance: "var(--nxr-accent)"', code)
		self.assertIn('voided: "var(--nxr-money-void)"', code)

	def test_expense_is_not_hardcoded_red_anymore(self) -> None:
		"""Regresión directa: antes `expense`/`voided` compartían el mismo rojo de
		Bootstrap con respaldo hexadecimal propio, contradiciendo la decisión ya escrita
		en el Design System de que el gasto legítimo no es rojo."""
		code = self.source()
		self.assertNotIn("--red-600", code)
		self.assertNotIn("--green-600", code)
		self.assertNotIn("--blue-600", code)
		self.assertNotIn("--blue-500", code)


class TestOperationalCssToneContract(unittest.TestCase):
	def test_global_tone_rule_uses_design_tokens(self) -> None:
		code = OPERATIONAL_CSS.read_text(encoding="utf-8")
		self.assertIn('[data-tone="income"]', code)
		self.assertIn("var(--nxr-money-in)", code)
		self.assertIn('[data-tone="expense"]', code)
		self.assertIn("var(--nxr-money-out)", code)
		self.assertIn('[data-tone="voided"]', code)
		self.assertIn("var(--nxr-money-void)", code)
		self.assertNotIn("--red-600", code)
		self.assertNotIn("--green-600", code)


class TestContractSummaryUsesMoneyBreakdown(unittest.TestCase):
	def source(self) -> str:
		return CONTRACTS.read_text(encoding="utf-8")

	def test_contract_summary_no_longer_uses_a_flat_definition_list(self) -> None:
		"""Las seis cifras del contrato (vigente/ejecutado/pagado/pendiente/anticipo/
		retención) tenían el mismo peso visual en una `<dl>` plana. No es un cambio de
		estilo aislado: es el mismo componente compartido que usa el resto de NEXORA."""
		code = self.source()
		self.assertNotIn("<dl><dt>", code)
		self.assertIn('class="nxr-ds-money-list"', code)
		self.assertIn("function moneyRow(", code)

	def test_contract_summary_distinguishes_spent_from_pending(self) -> None:
		code = self.source()
		self.assertIn('"spent"', code)
		self.assertIn('"pending"', code)
		self.assertIn('"reference"', code)
		# El monto vigente es la cifra de referencia; ejecutado y pagado ya salieron;
		# pendiente, anticipo y retención siguen abiertos.
		self.assertIn('moneyRow(__("Monto vigente")', code)
		self.assertIn('moneyRow(__("Ejecutado")', code)
		self.assertIn('moneyRow(__("Pagado")', code)
