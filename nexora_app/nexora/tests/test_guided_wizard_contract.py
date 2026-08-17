from __future__ import annotations

import pathlib
import unittest

PACKAGE = pathlib.Path(__file__).resolve().parents[1]
GUIDED = PACKAGE / "public/js/nexora_guided_operations.js"
CONSOLE = PACKAGE / "nexora/page/nexora_operations/nexora_operations.js"


class TestGuidedWizardContract(unittest.TestCase):
	"""El asistente no puede cerrar la revisión que el usuario acaba de pedir, ni creer
	que hay vista previa vigente cuando no la hay.

	Tres correcciones distintas (#67, #68, #72) intentaron resolver «Guided stage 4
	never opened» adivinando `state.reviewUsable` por sondeo: releer la consola
	original (`reviewValidity`) desde un `MutationObserver` con un temporizador de
	asentamiento (`SETTLE_MS`) para tolerar el parpadeo de sus botones al
	refrescarse. Cada arreglo tapaba una causa concreta del parpadeo y el fallo
	volvía a aparecer por otra — porque seguía siendo una adivinanza sobre un estado
	ajeno, no una notificación del cambio en el instante en que ocurre. La consola
	original (`nexora_operations.js`) ahora avisa con el evento
	`nexora:operation-preview-state` en el mismo instante en que la vista previa
	queda vigente o deja de estarlo, y `applyPreviewState` es la única función que
	escribe `state.reviewUsable`. Ya no hay sondeo que perdonar (Capítulo 51).
	"""

	def guided_source(self) -> str:
		return GUIDED.read_text(encoding="utf-8")

	def console_source(self) -> str:
		return CONSOLE.read_text(encoding="utf-8")

	def apply_preview_state_body(self) -> str:
		code = self.guided_source()
		self.assertIn("function applyPreviewState(root, state, valid) {", code)
		return code.split("function applyPreviewState(root, state, valid) {", 1)[1].split("\n\t}", 1)[0]

	def test_review_usable_is_written_only_by_apply_preview_state(self) -> None:
		code = self.guided_source()
		self.assertEqual(
			code.count("state.reviewUsable ="),
			1,
			"solo applyPreviewState puede fijar state.reviewUsable, o dos fuentes pueden discrepar",
		)
		body = self.apply_preview_state_body()
		self.assertIn("state.reviewUsable = valid;", body)

	def test_the_source_of_truth_is_the_event_not_a_poll(self) -> None:
		"""El sondeo con temporizador de asentamiento quedó fuera: ya no hay nada que
		esperar a que se asiente, porque la notificación llega en el instante exacto."""
		code = self.guided_source()
		self.assertNotIn("function reviewValidity(", code)
		self.assertNotIn("SETTLE_MS", code)
		self.assertNotIn("state.settleTimer", code)
		self.assertNotIn("state.invalidSince", code)
		self.assertIn('document.addEventListener("nexora:operation-preview-state"', code)
		listener = code.split('document.addEventListener("nexora:operation-preview-state"', 1)[1].split(
			"\n\t\t});", 1
		)[0]
		self.assertIn(
			"shell() !== root", listener, "el evento se ignora si el usuario ya no está en esta pantalla"
		)
		self.assertIn("applyPreviewState(root, state, Boolean(event.detail?.valid))", listener)

	def test_opening_the_review_does_not_consume_the_request(self) -> None:
		body = self.apply_preview_state_body()
		self.assertIn("activate(state, 3)", body)
		self.assertNotIn(
			"state.previewRequested = false",
			body,
			"consumir la bandera al abrir la etapa 3 vuelve la apertura dependiente de un tick",
		)

	def test_the_request_is_consumed_where_the_review_is_really_used(self) -> None:
		"""Sin consumirla en algún punto, la bandera quedaría encendida para siempre."""
		code = self.guided_source()
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
		válida: la corrección no debe haberla eliminado. Ya no espera a que un estado
		inválido se «asiente»: el evento solo llega cuando la consola original decidió
		de verdad que la vista previa dejó de ser válida, así que no hay parpadeo que
		perdonar."""
		body = self.apply_preview_state_body()
		self.assertIn("if (!valid && state.stage > 2) activate(state, 2, false);", body)

	def test_advancing_is_decided_by_the_same_value_that_disables_the_button(self) -> None:
		"""Pintar el botón y decidir si el clic avanza tienen que leer el mismo valor,
		o un desfase entre los dos puede dejar el botón encendido y el clic sin efecto
		en el mismo instante (Capítulo 39)."""
		code = self.guided_source()
		self.assertIn("if (target === 4 && !state.reviewUsable)", code)
		handler = code.split("if (target === 4 && !state.reviewUsable) {", 1)[1].split("\n\t\t\t\t}", 1)[0]
		self.assertIn("frappe.show_alert", handler)
		sync = code.split("function sync(root, state) {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn("const valid = state.reviewUsable;", sync)
		self.assertIn("if (next.disabled === valid) next.disabled = !valid;", sync)

	def test_the_original_console_notifies_both_directions(self) -> None:
		"""El asistente solo puede fiarse del evento si la consola original lo emite
		exactamente cuando la vista previa queda vigente y exactamente cuando deja de
		estarlo — no en un tercer punto donde alguien lo olvide."""
		code = self.console_source()
		self.assertEqual(
			code.count('new CustomEvent("nexora:operation-preview-state"'),
			2,
			"debe avisar en los dos sentidos: vigente e invalidada",
		)
		self.assertIn("detail: { valid: true } })", code)
		self.assertIn("detail: { valid: false, reason } })", code)
		# Se dispara dentro de invalidatePreview, que es el único lugar donde se anula
		# la vista previa: cualquier otro punto que la anule directamente rompería el contrato.
		invalidate = code.split('function invalidatePreview(reason = "unknown") {', 1)[1].split("\n\t}", 1)[0]
		self.assertIn('new CustomEvent("nexora:operation-preview-state"', invalidate)


if __name__ == "__main__":
	unittest.main()
