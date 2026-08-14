from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAGE = ROOT / "nexora/nexora/page/nexora_finance/nexora_finance.js"
WORKSPACE = ROOT / "nexora/nexora/workspace/nexora/nexora.json"


class TestFinancialUIContract(unittest.TestCase):
	def test_page_calls_real_preview_execute_and_source_services(self) -> None:
		text = PAGE.read_text(encoding="utf-8")
		for method in (
			"nexora.financial.service.preview_central_operation",
			"nexora.financial.service.execute_central_operation",
			"nexora.financial.service.list_central_operations",
			"nexora.financial.service.create_fund_source",
			"nexora.financial.service.list_source_balances",
			"nexora.financial.service.create_commitment",
			"nexora.financial.service.execute_commitment",
			"nexora.financial.service.release_commitment",
		):
			self.assertIn(method, text)
		self.assertNotIn("mock", text.lower())
		self.assertNotIn("simulad", text.lower())

	def test_execute_is_disabled_until_server_preview(self) -> None:
		text = PAGE.read_text(encoding="utf-8")
		self.assertIn('executeButton.prop("disabled", true)', text)
		self.assertIn('executeButton.prop("disabled", false)', text)
		self.assertIn("preview_hash", text)

	def test_operation_type_is_catalog_derived_and_profile_drives_fields(self) -> None:
		text = PAGE.read_text(encoding="utf-8")
		self.assertNotIn('fieldname: "operation_type"', text)
		self.assertIn('fieldname: "kernel_service"', text)
		self.assertIn("read_only: 1", text)
		self.assertIn("serviceForProfile", text)
		self.assertIn("applySelectedProfile", text)
		self.assertIn("applyCategoryVisibility", text)
		self.assertIn("profile.requires_reference", text)
		self.assertIn("profile.requires_due_date", text)
		self.assertIn("profile.requires_beneficiary", text)

	def test_dashboard_launch_context_is_consumed(self) -> None:
		text = PAGE.read_text(encoding="utf-8")
		self.assertIn("frappe.route_options?.nexora_action", text)
		self.assertIn("frappe.route_options?.project", text)
		self.assertIn('launchContext.action === "income"', text)
		self.assertIn('launchContext.action === "expense"', text)
		self.assertIn('operationCode.set_value("CONSTRUCTION_PAYMENT")', text)
		self.assertIn("await project.set_value(launchProject)", text)
		# Si la ruta no trae proyecto, se hereda del contexto activo en lugar de
		# obligar a elegirlo otra vez (salvo que la ruta traiga una acción propia).
		self.assertIn(
			"launchContext.project ||\n"
			"\t\t\t(!launchContext.action ? await window.nexora.context?.activeProject?.() : null) ||\n"
			"\t\t\tnull;",
			text,
		)

	def test_monetary_values_are_formatted_not_raw_interpolated(self) -> None:
		"""Every other NEXORA screen formats HNL amounts through Intl.NumberFormat (or
		the shared window.nexora.ui.formatMoney). A raw `L${value}` interpolation skips
		thousands separators and a fixed decimal count, and interpolates a server value
		straight into HTML instead of through a formatter that only ever returns
		digits, separators and a currency symbol."""
		text = PAGE.read_text(encoding="utf-8")
		self.assertNotRegex(text, r"L\$\{", "found a raw, unformatted HNL interpolation")
		self.assertIn("function money(value)", text)
		self.assertIn("window.nexora.ui?.formatMoney?.(value)", text)

	def test_remittance_form_calls_the_real_service_and_sums_destinations_client_side(self) -> None:
		"""Bloque 39. Mismo patrón que 'Alta rápida de fuente' (buildSourceFields):
		acción directa, sin paso de vista previa — la diferencia es que el importe
		total lo suman los destinos capturados, no un campo propio."""
		text = PAGE.read_text(encoding="utf-8")
		self.assertIn("nexora.financial.service.create_remittance", text)
		self.assertIn("function buildRemittanceFields(body) {", text)
		remittance_fn = text.split("function buildRemittanceFields(body) {", 1)[1]
		self.assertIn("destinations", remittance_fn)
		self.assertIn(
			"totalHnl = roundMoney(\n\t\t\t\tnormalizedDestinations.reduce((sum, row) => sum + Number(row.amount_hnl), 0)\n\t\t\t)",
			remittance_fn,
		)

	def test_remittance_original_amount_accounts_for_the_exchange_rate(self) -> None:
		"""Bloque 40, hallazgo real de auditoría (detectado en una revisión
		automatizada sobre una rama de trabajo, verificado a mano contra
		NXRRemittance.validate() antes de aceptarlo): los destinos se capturan
		en HNL, pero el servidor exige `original_amount` en moneda original y
		calcula `total_amount_hnl = original_amount * exchange_rate`. Enviar el
		total en HNL tal cual duplicaba la conversión en cualquier remesa con
		moneda distinta de HNL (tasa != 1) — nunca se detectó en pruebas porque
		todas usaban HNL con tasa 1, donde el error desaparece (x / 1 == x)."""
		text = PAGE.read_text(encoding="utf-8")
		remittance_fn = text.split("function buildRemittanceFields(body) {", 1)[1].split("\n\t}\n};", 1)[0]
		self.assertIn("original_amount: originalAmount", remittance_fn)
		self.assertIn("exchange_rate: exchangeRate", remittance_fn)
		self.assertIn("roundMoney(totalHnl / exchangeRate)", remittance_fn)
		# Y no se divide por una tasa inválida sin avisar.
		self.assertIn("exchangeRate <= 0", remittance_fn)

	def test_remittance_rounding_matches_the_server_before_submitting(self) -> None:
		"""Segundo hallazgo (misma auditoría, misma disciplina de verificación
		manual antes de aceptarlo): incluso con la conversión corregida,
		NXRRemittance.validate() cuantiza `original_amount` a 2 decimales
		*antes* de multiplicarlo por la tasa (`money()`, financial/model_utils.py),
		así que `total_amount_hnl` puede no coincidir con la suma de los destinos
		por más de un centavo en cuanto la tasa no es 1 — no es ruido de punto
		flotante, es el mismo redondeo que hará el servidor, replicado aquí para
		que la suma cuadre exactamente antes de enviarla."""
		text = PAGE.read_text(encoding="utf-8")
		self.assertIn("function roundMoney(value) {", text)
		self.assertIn("function roundRate(value) {", text)
		remittance_fn = text.split("function buildRemittanceFields(body) {", 1)[1].split("\n\t}\n};", 1)[0]
		self.assertIn("const expectedTotalHnl = roundMoney(originalAmount * exchangeRate)", remittance_fn)
		self.assertIn("if (expectedTotalHnl !== totalHnl) {", remittance_fn)
		# El último destino absorbe la diferencia, no uno arbitrario.
		self.assertIn("normalizedDestinations[normalizedDestinations.length - 1]", remittance_fn)

	def test_remittance_destination_amounts_are_quantized_before_summing(self) -> None:
		"""Tercer hallazgo (misma auditoría): el servidor cuantiza cada fila con
		money(row.amount_hnl) antes de sumarlas (NXRRemittance.validate). Un
		destino con más de 2 decimales —pegado, no tecleado, el input no lo
		impide— hacía que la suma vista aquí no fuera la que vería el servidor,
		reabriendo el mismo desajuste que el fix anterior cerró para el total."""
		text = PAGE.read_text(encoding="utf-8")
		remittance_fn = text.split("function buildRemittanceFields(body) {", 1)[1].split("\n\t}\n};", 1)[0]
		self.assertIn(
			"normalizedDestinations = destinations.map((row) => ({\n"
			"\t\t\t\t...row,\n"
			"\t\t\t\tamount_hnl: roundMoney(Number(row.amount_hnl)).toFixed(2),\n"
			"\t\t\t}));",
			remittance_fn,
		)
		self.assertIn("destinations: normalizedDestinations,", remittance_fn)

	def test_remittance_rounding_adjustment_cannot_leave_a_destination_at_zero_or_below(self) -> None:
		"""Cuarto hallazgo (misma auditoría): NXRFundSource.validate() rechaza
		original_amount <= 0. El ajuste de redondeo (el último destino absorbe
		la diferencia) podía dejarlo en cero o negativo para tasas y montos
		realistas (comprobado con Decimal real: L1000.02 a tasa 24.567891234
		produce un ajuste de -0.11, suficiente para hundir un destino pequeño),
		abortando toda la remesa a mitad de transacción con un error genérico
		en vez de pedirle al usuario que ajuste los importes antes de enviar."""
		text = PAGE.read_text(encoding="utf-8")
		remittance_fn = text.split("function buildRemittanceFields(body) {", 1)[1].split("\n\t}\n};", 1)[0]
		self.assertIn("if (adjusted <= 0) {", remittance_fn)
		guard_block = remittance_fn.split("if (adjusted <= 0) {", 1)[1].split(
			"lastDestination.amount_hnl = adjusted.toFixed(2);", 1
		)[0]
		self.assertIn("return;", guard_block)

	def test_workspace_links_to_real_page(self) -> None:
		payload = json.loads(WORKSPACE.read_text(encoding="utf-8"))
		shortcut = next(row for row in payload["shortcuts"] if row["label"] == "Núcleo de Fondos")
		self.assertEqual("Page", shortcut["type"])
		self.assertEqual("nexora-finance", shortcut["link_to"])


if __name__ == "__main__":
	unittest.main()
