from __future__ import annotations

import pathlib
import unittest

PACKAGE = pathlib.Path(__file__).resolve().parents[1]
OPERATIONS = PACKAGE / "nexora/page/nexora_operations/nexora_operations.js"
CLOSING = PACKAGE / "nexora/page/nexora_closing/nexora_closing.js"


class TestOperationalResultContract(unittest.TestCase):
	"""NXR-UX-0012 — resultado explicable.

	Antes de este bloque, contabilizar una operación solo dejaba un
	`frappe.show_alert` con el número de documento; desaparecía en unos segundos y no
	explicaba el efecto real sobre los fondos. El servidor ya devolvía `sources` con
	saldo anterior/posterior por fuente en la respuesta de `execute_operational_movement`
	(lo mismo que usa la vista previa) — nadie lo leía. Estas pruebas verifican que el
	panel de resultado use esos datos ya existentes, no que se haya inventado un cálculo
	nuevo en el cliente.
	"""

	def source(self) -> str:
		return OPERATIONS.read_text(encoding="utf-8")

	def test_a_persistent_result_panel_exists_next_to_the_preview(self) -> None:
		code = self.source()
		self.assertIn('class="nxr-operational-result nxr-card" hidden', code)
		self.assertIn('class="nxr-result-body"', code)

	def test_render_result_uses_the_response_the_server_already_sends(self) -> None:
		code = self.source()
		self.assertIn("function renderResult(result, data)", code)
		body = code.split("function renderResult(result, data) {", 1)[1].split("\n\t}", 1)[0]
		# No inventa un cálculo nuevo: usa result.sources, result.document_number y
		# result.document_date, que execute_operational_movement ya devuelve.
		self.assertIn("result.document_number", body)
		self.assertIn("result.sources", body)
		self.assertIn("result.document_date", body)
		self.assertIn("sourceBalanceTable(result.sources)", body)
		self.assertIn("panel.removeAttr(\"hidden\")", body)

	def test_the_preview_and_result_tables_share_one_row_renderer(self) -> None:
		"""Antes había una sola tabla de saldos (la de la vista previa); ahora hay dos
		lugares que necesitan la misma forma de fila. Duplicar el HTML de la fila habría
		sido la forma fácil de desalinearlas la primera vez que alguien cambie una."""
		code = self.source()
		self.assertEqual(1, code.count("function sourceBalanceRows("), "una sola definición")
		self.assertEqual(1, code.count("function sourceBalanceTable("), "una sola definición")
		self.assertIn("sourceBalanceTable(preview.sources)", code)
		self.assertIn("sourceBalanceTable(result.sources)", code)

	def test_execute_movement_renders_the_result_in_addition_to_the_toast(self) -> None:
		code = self.source()
		execute_body = code.split("async function executeMovement() {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn("frappe.show_alert(", execute_body, "el aviso rápido se conserva")
		self.assertIn("renderResult(response.message, data)", execute_body)

	def test_weekly_close_uses_the_shared_error_helper_not_a_hand_rolled_one(self) -> None:
		"""NXR-UX-0012 también es consistencia: nexora_closing.js mostraba un mensaje fijo
		en los tres `catch`, descartando el motivo real que el servidor ya calculaba
		(el mismo defecto que Bloque 11 corrigió en nexora_reports.js). Las otras nueve
		pantallas del producto ya usan `window.nexora.ui.showError`."""
		code = CLOSING.read_text(encoding="utf-8")
		self.assertEqual(
			3,
			code.count("window.nexora.ui.showError(error, {"),
			"los tres manejadores de error del cierre semanal deben usar el helper compartido",
		)
		self.assertNotIn(
			'frappe.msgprint({ title: __("No fue posible',
			code,
			"no debe quedar un mensaje de error fijo que ignore la razón real del servidor",
		)
