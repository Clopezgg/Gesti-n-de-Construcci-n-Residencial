from __future__ import annotations

import pathlib
import unittest

PACKAGE = pathlib.Path(__file__).resolve().parents[1]
GUIDED = PACKAGE / "public/js/nexora_guided_operations.js"


class TestGuidedWizardContract(unittest.TestCase):
	"""El asistente no puede cerrar la revisión que el usuario acaba de pedir.

	`previewRequested` se consumía en la primera pasada de `sync()` que viera el
	estado válido. Si el estado parpadeaba a inválido justo después —cosa que la
	consola original hace al refrescar botones—, la regla de degradación devolvía
	el asistente a la etapa 2 con la bandera ya gastada y la revisión no volvía a
	abrirse nunca: el usuario pulsaba «Vista previa», el servidor respondía bien y
	el asistente retrocedía en silencio. Costó dos rojos del recorrido de navegador.
	"""

	def source(self) -> str:
		return GUIDED.read_text(encoding="utf-8")

	def sync_body(self) -> str:
		code = self.source()
		self.assertIn("state.previewRequested", code, "el asistente perdió la bandera de revisión")
		return code.split("if (valid && state.previewRequested)", 1)[1].split("\n\t}", 1)[0]

	def test_opening_the_review_does_not_consume_the_request(self) -> None:
		body = self.sync_body()
		self.assertIn("activate(state, 3)", body)
		self.assertNotIn(
			"state.previewRequested = false",
			body,
			"consumir la bandera al abrir la etapa 3 vuelve la apertura dependiente de un tick",
		)

	def test_the_request_is_consumed_where_the_review_is_really_used(self) -> None:
		"""Sin consumirla en algún punto, la bandera quedaría encendida para siempre."""
		code = self.source()
		self.assertIn(
			"if (target === 4) state.previewRequested = false;",
			code,
			"la revisión se consume al avanzar al registro definitivo",
		)
		listener = code.split('document.addEventListener("nexora:data-changed"', 1)[1]
		listener = listener.split("\n\t\t});", 1)[0]
		self.assertIn(
			"state.previewRequested = false",
			listener,
			"un cambio de datos invalida la revisión pedida",
		)

	def test_the_demotion_rule_still_guards_an_invalid_state(self) -> None:
		"""La degradación a la etapa 2 es la que protege de registrar sin vista previa
		válida: la corrección no debe haberla eliminado."""
		self.assertIn("if (!valid && state.stage > 2) activate(state, 2, false);", self.source())


if __name__ == "__main__":
	unittest.main()
