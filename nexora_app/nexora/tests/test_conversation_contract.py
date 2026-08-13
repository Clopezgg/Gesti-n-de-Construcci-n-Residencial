"""Pruebas de contrato estático del Bloque 18 (NXR-CNV-0001).

Verifican estructura real de código/JSON sin ejecutar Frappe: que el catálogo
declarativo tiene exactamente las intenciones esperadas, que los DocTypes
nuevos están bloqueados a escritura directa (mismo patrón que
``NXR Audit Event``), y que la página nueva está registrada en los cuatro
lugares que exige el invariante de gobernanza establecido en el Bloque 17.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]


class TestConversationRegistry(unittest.TestCase):
	def setUp(self) -> None:
		import sys

		sys.path.insert(0, str(APP_ROOT))
		from nexora.conversation.core import IntentKind
		from nexora.conversation.registry import REGISTRY

		self.REGISTRY = REGISTRY
		self.IntentKind = IntentKind

	def test_registry_has_exactly_the_seven_minimum_intents_of_the_mission(self) -> None:
		expected = {
			"query_fund_balance",
			"query_pending_payments",
			"query_contract",
			"register_expense",
			"register_income",
			"register_evidence",
			"create_purchase_request",
		}
		self.assertEqual(expected, set(self.REGISTRY.keys()))

	def test_every_write_intent_has_a_real_execute_method_dotted_path(self) -> None:
		for spec in self.REGISTRY.values():
			if spec.kind is self.IntentKind.WRITE:
				self.assertTrue(spec.execute_method, spec.key)
				self.assertRegex(spec.execute_method, r"^nexora\.[a-z_.]+$", spec.key)

	def test_no_intent_reimplements_a_movement_catalog_or_permission_action(self) -> None:
		"""El catálogo solo declara rutas punteadas a funciones reales — nunca un
		código de movimiento ni una acción de permiso escritos aquí en vez de en
		el dominio (`_build_write_payload` en `dispatch.py` es lo único que
		conoce `movement_code`, y solo para dos claves)."""
		source = (APP_ROOT / "conversation/registry.py").read_text(encoding="utf-8")
		self.assertNotIn("movement_code", source)
		self.assertNotIn("require_action", source)
		self.assertNotIn("require_project_access", source)


class TestDispatchModule(unittest.TestCase):
	def source(self) -> str:
		return (APP_ROOT / "conversation/dispatch.py").read_text(encoding="utf-8")

	def test_exposes_exactly_three_whitelisted_entrypoints(self) -> None:
		source = self.source()
		self.assertEqual(3, source.count('@frappe.whitelist(methods=["POST"])'))
		for name in ("def send_message", "def confirm_pending_intent", "def cancel_pending_intent"):
			self.assertIn(name, source)

	def test_send_message_rejects_guest_before_any_interpretation(self) -> None:
		source = self.source()
		guest_check = source.index('frappe.session.user == "Guest"')
		nlu_call = source.index("nlu.interpret(")
		self.assertLess(guest_check, nlu_call, "el asistente no debe interpretar texto de un invitado")

	def test_reads_and_writes_are_always_invoked_via_the_registry_dotted_path(self) -> None:
		"""El despachador nunca debe construir su propia consulta de saldo/contrato
		— siempre delega en `frappe.get_attr(spec.read_method)`/`spec.execute_method`."""
		source = self.source()
		self.assertIn("frappe.get_attr(spec.read_method)", source)
		self.assertIn("frappe.get_attr(spec.execute_method)", source)

	def test_write_execution_is_always_audited(self) -> None:
		source = self.source()
		self.assertIn('audit(\n\t\t"conversation_intent_executed"', source)
		self.assertIn('audit(\n\t\t"conversation_intent_cancelled"', source)

	def test_confirmation_requires_the_pending_intent_to_actually_be_awaiting_confirmation(self) -> None:
		source = self.source()
		self.assertIn('if doc.status != "AwaitingConfirmation":', source)

	def test_text_based_confirm_and_cancel_words_are_recognised(self) -> None:
		source = self.source()
		self.assertIn("_CONFIRM_WORDS", source)
		self.assertIn("_CANCEL_WORDS", source)
		self.assertIn("confirmar", source)
		self.assertIn("cancelar", source)


class TestPendingIntentDoctypeIsLockedToServiceWrites(unittest.TestCase):
	def test_every_new_conversation_doctype_forbids_direct_create_and_write(self) -> None:
		for doctype_dir in (
			"nxr_conversation",
			"nxr_conversation_message",
			"nxr_conversation_pending_intent",
		):
			path = APP_ROOT / f"nexora/doctype/{doctype_dir}/{doctype_dir}.json"
			payload = json.loads(path.read_text(encoding="utf-8"))
			self.assertEqual("NEXORA", payload["module"], doctype_dir)
			for permission in payload["permissions"]:
				self.assertEqual(0, permission.get("create", 0), f"{doctype_dir}: {permission}")
				self.assertEqual(0, permission.get("write", 0), f"{doctype_dir}: {permission}")

	def test_every_new_conversation_doctype_controller_requires_service_write(self) -> None:
		for doctype_dir in (
			"nxr_conversation",
			"nxr_conversation_message",
			"nxr_conversation_pending_intent",
		):
			path = APP_ROOT / f"nexora/doctype/{doctype_dir}/{doctype_dir}.py"
			source = path.read_text(encoding="utf-8")
			self.assertIn("require_service_write()", source)

	def test_pending_intent_status_options_match_the_pure_state_machine(self) -> None:
		import sys

		sys.path.insert(0, str(APP_ROOT))
		from nexora.conversation.core import PENDING_INTENT_TRANSITIONS

		path = (
			APP_ROOT / "nexora/doctype/nxr_conversation_pending_intent/nxr_conversation_pending_intent.json"
		)
		payload = json.loads(path.read_text(encoding="utf-8"))
		status_field = next(field for field in payload["fields"] if field["fieldname"] == "status")
		options = set(status_field["options"].split("\n"))
		self.assertEqual(set(PENDING_INTENT_TRANSITIONS.keys()), options)

	def test_pending_intent_controller_enforces_the_pure_transition_function(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_conversation_pending_intent/nxr_conversation_pending_intent.py"
		source = path.read_text(encoding="utf-8")
		self.assertIn("assert_pending_intent_transition", source)


class TestAssistantPageRegistration(unittest.TestCase):
	"""Mismo invariante de gobernanza que corrigió el Bloque 17: toda página
	nueva debe alcanzarse desde `nexora.js`, el workspace y `nexora_shell.js`,
	y todo bundle nuevo en `hooks.py` debe estar en el precache de la PWA."""

	def test_page_files_exist(self) -> None:
		page_dir = APP_ROOT / "nexora/page/nexora_assistant"
		self.assertTrue((page_dir / "nexora_assistant.json").is_file())
		self.assertTrue((page_dir / "nexora_assistant.js").is_file())
		self.assertTrue((page_dir / "__init__.py").is_file())

	def test_registered_in_global_destinations(self) -> None:
		source = (APP_ROOT / "public/js/nexora.js").read_text(encoding="utf-8")
		self.assertIn('href: "/app/nexora-assistant"', source)

	def test_registered_in_workspace_shortcuts_and_content(self) -> None:
		source = (APP_ROOT / "nexora/workspace/nexora/nexora.json").read_text(encoding="utf-8")
		self.assertIn('"link_to": "nexora-assistant"', source)
		self.assertIn("asistente_nexora", source)

	def test_registered_in_shell_sections(self) -> None:
		source = (APP_ROOT / "public/js/nexora_shell.js").read_text(encoding="utf-8")
		self.assertIn('route: "nexora-assistant"', source)

	def test_css_bundle_registered_in_hooks_and_pwa_precache(self) -> None:
		hooks_source = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
		worker_source = (APP_ROOT / "www/nexora-service-worker.js").read_text(encoding="utf-8")
		self.assertIn("nexora_assistant.css", hooks_source)
		self.assertIn("nexora_assistant.css", worker_source)

	def test_page_calls_only_the_three_real_dispatch_methods(self) -> None:
		source = (APP_ROOT / "nexora/page/nexora_assistant/nexora_assistant.js").read_text(encoding="utf-8")
		self.assertIn("nexora.conversation.dispatch.send_message", source)
		self.assertIn("nexora.conversation.dispatch.${method}", source)
		self.assertIn("confirm_pending_intent", source)
		self.assertIn("cancel_pending_intent", source)

	def test_page_never_computes_money_or_permission_logic_itself(self) -> None:
		source = (APP_ROOT / "nexora/page/nexora_assistant/nexora_assistant.js").read_text(encoding="utf-8")
		for forbidden in ("require_action", "movement_code", "amount_hnl *", "preview_hash ="):
			self.assertNotIn(forbidden, source)

	def test_confirm_and_cancel_cannot_be_double_dispatched(self) -> None:
		"""`send()` ya se protegía con una bandera `sending`; `resolvePending()`
		(botones "Confirmar"/"Cancelar" de una intención pendiente — puede ser un
		pago real) no tenía la misma guarda: un doble clic podía disparar
		`confirm_pending_intent` dos veces antes de que llegara la primera
		respuesta. El servidor ya es idempotente por `idempotency_key` (Bloque 28,
		auditoría), así que no hay riesgo de doble ejecución financiera, pero el
		doble clic sí producía una segunda llamada de red y podía mostrarle al
		usuario el error interno de idempotencia en vez de nada. Esta prueba fija
		que la pantalla también se protege del lado del cliente."""
		source = (APP_ROOT / "nexora/page/nexora_assistant/nexora_assistant.js").read_text(encoding="utf-8")
		self.assertIn("let resolving = false;", source)
		body = source.split("async function resolvePending(method) {", 1)[1].split("\n\t}\n", 1)[0]
		self.assertIn("if (resolving) return;", body)
		self.assertIn("resolving = true;", body)
		self.assertIn('.prop("disabled", true)', body)
		self.assertIn("resolving = false;", body)


class TestSearchAssistantIntegration(unittest.TestCase):
	"""NXR-UX-0009: el buscador universal (`nexora-search`) no tenía forma de
	responder una consulta en lenguaje natural ni de iniciar una acción — solo
	buscaba coincidencias literales de documento/nombre/cuenta/referencia. Estas
	pruebas fijan que la solución reutiliza el mismo motor conversacional que ya
	usa `nexora-assistant` (mismos tres métodos whitelisted, mismo permiso
	`view_reports` aplicado en el servidor) en vez de construir una segunda
	interpretación."""

	def _source(self) -> str:
		return (APP_ROOT / "nexora/page/nexora_search/nexora_search.js").read_text(encoding="utf-8")

	def test_classic_keyword_search_is_unchanged(self) -> None:
		source = self._source()
		self.assertIn("nexora.boot.universal_search_consolidated", source)
		self.assertIn("nexora.boot.get_search_result_detail", source)

	def test_falls_back_to_the_real_conversational_engine_on_empty_results(self) -> None:
		source = self._source()
		self.assertIn("nexora.conversation.dispatch.send_message", source)
		self.assertIn("nexora.conversation.dispatch.${method}", source)
		self.assertIn("confirm_pending_intent", source)
		self.assertIn("cancel_pending_intent", source)
		results_fn = source.split("function renderResults(results) {", 1)[1]
		self.assertIn("askAssistant(controls.query.get_value())", results_fn.split("\n\t}\n", 1)[0])

	def test_page_never_computes_money_or_permission_logic_itself(self) -> None:
		source = self._source()
		for forbidden in ("require_action", "movement_code", "amount_hnl *", "preview_hash ="):
			self.assertNotIn(forbidden, source)

	def test_confirm_and_cancel_cannot_be_double_dispatched(self) -> None:
		"""Mismo patrón que fijó `test_confirm_and_cancel_cannot_be_double_dispatched`
		para `nexora-assistant` (Bloque 28): un doble clic en «Confirmar»/«Cancelar»
		no debe disparar una segunda llamada de red mientras la primera sigue en
		vuelo."""
		source = self._source()
		self.assertIn("let searchAssistantBusy = false;", source)
		handler = source.split('"[data-search-assistant-confirm], [data-search-assistant-cancel]",', 1)[
			1
		].split("function renderResults(results) {", 1)[0]
		self.assertIn("if (searchAssistantBusy) return;", handler)
		self.assertIn("searchAssistantBusy = true;", handler)
		self.assertIn('.prop("disabled", true)', handler)
		self.assertIn("searchAssistantBusy = false;", handler)


class TestDesignSystemReuse(unittest.TestCase):
	def test_stylesheet_never_redefines_a_design_system_component_class(self) -> None:
		"""Regresión directa del hallazgo real de este mismo bloque: la primera
		versión de `nexora_assistant.css` sobrescribía `.nxr-ds-btn` desde un
		selector descendiente y el gate de diseño (`test_design_system_contract.py`)
		lo rechazó correctamente. Esta prueba fija esa corrección."""
		source = (APP_ROOT / "public/css/nexora_assistant.css").read_text(encoding="utf-8")
		without_comments = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
		self.assertNotIn(".nxr-ds-", without_comments)


if __name__ == "__main__":
	unittest.main()
