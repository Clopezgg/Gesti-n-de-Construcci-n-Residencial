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
		válida: la corrección no debe haberla eliminado. Ahora se dispara con el estado
		**asentado**, no con el instantáneo: la consola original apaga y enciende sus
		botones al refrescarse, y ese parpadeo devolvía al usuario a la etapa 2 sin que
		hubiera cambiado nada."""
		code = self.source()
		self.assertIn("if (settledInvalid && state.stage > 2) activate(state, 2, false);", code)
		self.assertNotIn("if (!valid && state.stage > 2)", code)
		# «Asentado» tiene que significar algo: un umbral y un reintento programado, o el
		# estado inválido sin más mutaciones no se revisaría nunca.
		self.assertIn("const SETTLE_MS =", code)
		self.assertIn("Date.now() - state.invalidSince >= SETTLE_MS", code)
		self.assertIn("state.settleTimer = setTimeout(schedule,", code)

	def test_advancing_is_decided_by_the_settled_truth_not_by_a_blink(self) -> None:
		"""`go.disabled` es estado de pintado y parpadea; se corrigió mirando
		`reviewValidity(root)` en el manejador del clic. Pero esa lectura también
		parpadea: la consola original apaga y enciende sus botones al refrescarse, y
		`sync` ya sabía perdonar ese parpadeo pintando el botón con el estado
		**asentado** (`usable`, con margen `SETTLE_MS`). El manejador del clic seguía
		comprobando el estado **instantáneo**: el botón se veía habilitado, el clic caía
		justo en el parpadeo y la etapa 4 nunca se abría sin que nada pareciera roto. El
		recorrido real lo mostró así: «Guided stage 4 never opened» con la vista previa
		vigente y el botón habilitado (Capítulo 39). Pintar y decidir tienen que leer el
		mismo valor asentado, no dos cálculos que puedan discrepar durante `SETTLE_MS`."""
		code = self.source()
		self.assertIn("function reviewValidity(root)", code)
		self.assertIn("if (target === 4 && !state.reviewUsable)", code)
		self.assertNotIn("if (target === 4 && !reviewValidity(root))", code)
		self.assertNotIn("if (target === 4 && go.disabled) return;", code)
		handler = code.split("if (target === 4 && !state.reviewUsable) {", 1)[1].split("\n\t\t\t\t}", 1)[0]
		self.assertIn("frappe.show_alert", handler)
		# Pintar y decidir leen el mismo valor: `sync` calcula `usable` una sola vez y lo
		# guarda en `state.reviewUsable` antes de usarlo para pintar el botón.
		sync = code.split("function sync(root, state) {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn("const usable = valid || !settledInvalid;", sync)
		self.assertIn("state.reviewUsable = usable;", sync)
		self.assertLess(
			sync.index("state.reviewUsable = usable;"),
			sync.index("if (next.disabled === usable) next.disabled = !usable;"),
			"el estado compartido se guarda antes de pintar el botón con el mismo valor",
		)


if __name__ == "__main__":
	unittest.main()
