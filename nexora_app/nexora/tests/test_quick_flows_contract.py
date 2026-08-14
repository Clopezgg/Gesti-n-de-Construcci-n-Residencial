from __future__ import annotations

import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestQuickFlowsContract(unittest.TestCase):
	def test_shared_coordinator_is_loaded_after_primary_product_script(self) -> None:
		hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
		self.assertLess(
			hooks.index("/assets/nexora/js/nexora.js"),
			hooks.index("/assets/nexora/js/nexora_quick_flows.js"),
		)

	def test_income_and_expense_accesses_converge_on_operational_engine(self) -> None:
		code = (APP_ROOT / "public/js/nexora_quick_flows.js").read_text(encoding="utf-8")
		for selector in (
			".nxr-quick-income",
			'[data-action="income"]',
			"[data-launch-income]",
			".nxr-quick-expense",
			'[data-action="expense"]',
			'[data-operation="CONSTRUCTION_PAYMENT"]',
		):
			self.assertIn(selector, code)
		self.assertIn('openOperationalFlow("101")', code)
		self.assertIn('openOperationalFlow("102")', code)
		self.assertIn('frappe.set_route("nexora-operations")', code)
		self.assertNotIn("preview_central_operation", code)
		self.assertNotIn("execute_central_operation", code)

	def test_context_period_and_duplicate_submission_are_guarded(self) -> None:
		code = (APP_ROOT / "public/js/nexora_quick_flows.js").read_text(encoding="utf-8")
		for marker in (
			"nexora:guided-operation-context",
			"Fecha fuera del período activo",
			"from_date",
			"to_date",
			"installServerExecutionGuard",
			"executionInFlight",
			"executionKeys",
			"aria-busy",
			"stopImmediatePropagation",
			"NEXORA_DUPLICATE_SUBMISSION_BLOCKED",
		):
			self.assertIn(marker, code)
		self.assertNotIn("}, 30000)", code)

	def test_frappe_thenables_are_awaited_without_chained_finally(self) -> None:
		quick = (APP_ROOT / "public/js/nexora_quick_flows.js").read_text(encoding="utf-8")
		context = (APP_ROOT / "public/js/nexora_report_actions.js").read_text(encoding="utf-8")
		self.assertIn("const response = await request", quick)
		self.assertIn("const response = await frappe.call", context)
		self.assertNotIn("frappe\n\t\t\t.call", context)
		self.assertNotIn(
			".catch((error) => {\n",
			context[
				context.index("async function loadContext") : context.index("async function updateContext")
			],
		)

	def test_guided_expense_preserves_server_preview_and_fund_selection_ui(self) -> None:
		quick = (APP_ROOT / "public/js/nexora_quick_flows.js").read_text(encoding="utf-8")
		page = (APP_ROOT / "nexora/page/nexora_operations/nexora_operations.js").read_text(encoding="utf-8")
		self.assertIn("saldo anterior, importe afectado y saldo resultante", quick)
		self.assertIn('data-detail-tab="funds"', page)
		self.assertIn("allocations()", page)
		self.assertIn("preview_operational_movement", page)
		self.assertIn("execute_operational_movement", page)
		self.assertIn("preview_hash", page)
		self.assertIn("idempotency_key", page)

	def test_document_actions_preserve_original_and_use_audited_services(self) -> None:
		code = (APP_ROOT / "public/js/nexora_quick_flows.js").read_text(encoding="utf-8")
		for label in (
			"Corregir fecha o datos",
			"Corregir importe",
			"Sustituir documento",
			"Anular operación",
			"Revertir operación",
			"Ver historial",
			"Descargar",
		):
			self.assertIn(label, code)
		self.assertIn("El original no será eliminado ni sobrescrito", code)
		self.assertIn("preview_operational_movement", code)
		self.assertIn("execute_operational_movement", code)
		self.assertIn("reference_name: frm.docname", code)
		self.assertIn("preview_hash", code)
		self.assertIn("idempotency_key", code)
		self.assertIn("al menos 10 caracteres", code)
		self.assertIn("La transacción se revirtió", code)

	def test_controlled_corrections_require_three_distinct_users(self) -> None:
		code = (APP_ROOT / "public/js/nexora_quick_flows.js").read_text(encoding="utf-8")
		shared = (APP_ROOT / "public/js/nexora.js").read_text(encoding="utf-8")
		operations = (APP_ROOT / "nexora/page/nexora_operations/nexora_operations.js").read_text(
			encoding="utf-8"
		)
		rules = (APP_ROOT / "financial/reference_rules.py").read_text(encoding="utf-8")
		for marker in (
			'fieldname: "requester"',
			'fieldname: "approved_by"',
			'options: "User"',
			"correctionActors(values)",
			"state.idempotencyKey ||= uuid()",
		):
			self.assertIn(marker, code)
		# La regla vive en `window.nexora.rules` para que las dos superficies que
		# registran correcciones —el diálogo del documento y la consola operativa— no
		# puedan divergir. La consola no la aplicaba: elegirse a uno mismo como
		# solicitante se rechazaba recién en la vista previa del servidor.
		self.assertIn("Solicitante, aprobador y ejecutor deben ser tres usuarios distintos.", shared)
		self.assertIn("segregationError(requester, approvedBy)", shared)
		for surface, source in (("quick_flows", code), ("operations", operations)):
			with self.subTest(surface=surface):
				self.assertIn("window.nexora.rules.segregationError(", source)
				self.assertNotIn("new Set([requester, approvedBy, executor])", source)
		self.assertNotIn("requester: frappe.session.user", code)
		self.assertNotIn("approved_by: frappe.session.user", code)
		self.assertIn("len(set(identities)) != 3", rules)
		for operation_code in ("REVERSAL_NO_CASH", "DOCUMENT_SUBSTITUTION"):
			self.assertIn(operation_code, rules)

	def test_mobile_cards_preserve_desktop_tables_and_accessibility(self) -> None:
		code = (APP_ROOT / "public/js/nexora_quick_flows.js").read_text(encoding="utf-8")
		css = (APP_ROOT / "public/css/nexora_dashboard_fixes.css").read_text(encoding="utf-8")
		for marker in (
			"tableToMobileCards",
			"nxr-mobile-operation-card",
			"Documento",
			"Importe",
			"Estado",
			"operational-ledger",
			"search-results",
			"mobileSignature",
		):
			self.assertIn(marker, code)
		for marker in (
			"@media (max-width: 600px)",
			"env(safe-area-inset-bottom)",
			"min-height: 44px",
			"touch-action: manipulation",
			"prefers-reduced-motion",
			"aria-busy",
		):
			self.assertIn(marker, css if marker != "aria-busy" else code + css)
		self.assertIn(".nxr-mobile-cards {\n\tdisplay: none;", css)

	def test_search_is_consolidated_and_vocabulary_is_consistent(self) -> None:
		ui = (APP_ROOT / "public/js/nexora_report_actions.js").read_text(encoding="utf-8")
		quick = (APP_ROOT / "public/js/nexora_quick_flows.js").read_text(encoding="utf-8")
		search = (APP_ROOT / "nexora/page/nexora_search/nexora_search.js").read_text(encoding="utf-8")
		boot = (APP_ROOT / "boot.py").read_text(encoding="utf-8")
		for marker in (
			"universal_search_consolidated",
			"get_search_result_detail",
			"NXR Financial Account",
			"NXR Operation Effect",
			"require_project_access",
			"frappe.has_permission",
		):
			self.assertIn(marker, boot)
		for marker in (
			"documento de 12 dígitos",
			"Vista consolidada",
			"Efecto financiero",
			"Relaciones e historial",
			"Abrir comprobante",
			"Abrir documento",
		):
			self.assertIn(marker, search)
		for marker in (
			"Registrar definitivamente",
			"Tipo de movimiento",
			"Cuenta guardada",
			"Comprobante",
			"Historial financiero",
		):
			self.assertIn(marker, ui + quick)
		self.assertIn("normalizeVisibleVocabulary", quick)

	def test_search_endpoints_are_overridden_with_permission_aware_queries(self) -> None:
		hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
		permissions = (APP_ROOT / "permissions.py").read_text(encoding="utf-8")
		self.assertIn(
			'"nexora.dashboard.service.universal_search": "nexora.permissions.secure_universal_search"',
			hooks,
		)
		self.assertIn(
			'"nexora.boot.universal_search_consolidated": "nexora.permissions.secure_universal_search_consolidated"',
			hooks,
		)
		for marker in (
			"frappe.get_list",
			"frappe.has_permission",
			"require_project_access",
			"_row_is_readable",
			"_masked_account",
		):
			self.assertIn(marker, permissions)
		self.assertNotIn("frappe.get_all(", permissions)

	def test_dashboard_currency_guard_remains_active(self) -> None:
		code = (APP_ROOT / "public/js/nexora_quick_flows.js").read_text(encoding="utf-8")
		self.assertIn("escapedCurrencyMarkup", code)
		self.assertIn("normalizeDashboardCurrency", code)
		self.assertIn("node.textContent = match[1].trim()", code)
		self.assertIn("new MutationObserver", code)

	def test_the_correction_promise_lives_in_its_own_element(self) -> None:
		"""«El original no será eliminado ni sobrescrito» es la promesa que sostiene toda
		la corrección auditada: el usuario acepta anular porque confía en que nada se
		pierde. Como nodo de texto suelto dentro del `alert` no se puede estilar, traducir
		como unidad ni comprobar —el recorrido de navegador la buscaba con `exact: true` y
		nunca podía encontrarla, porque el elemento contenedor incluye también el título—.
		"""
		flows = (APP_ROOT / "public/js/nexora_quick_flows.js").read_text(encoding="utf-8")
		self.assertIn('<span class="nxr-correction-preserves">', flows)
		promise = flows.split('<span class="nxr-correction-preserves">', 1)[1].split("</span>", 1)[0]
		self.assertIn("El original no será eliminado ni sobrescrito.", promise)
		# El título no puede volver a compartir elemento con la promesa.
		self.assertNotIn("movement_label", promise)


if __name__ == "__main__":
	unittest.main()
