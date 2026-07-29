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
			'.nxr-quick-income',
			'[data-action="income"]',
			'[data-launch-income]',
			'.nxr-quick-expense',
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

	def test_guided_expense_preserves_server_preview_and_multifund_ui(self) -> None:
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
		rules = (APP_ROOT / "financial/reference_rules.py").read_text(encoding="utf-8")
		for marker in (
			'fieldname: "requester"',
			'fieldname: "approved_by"',
			'options: "User"',
			"Solicitante, aprobador y ejecutor deben ser tres usuarios distintos.",
			"correctionActors(values)",
			"state.idempotencyKey ||= uuid()",
		):
			self.assertIn(marker, code)
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
		search = (APP_ROOT / "nexora/page/nexora-search/nexora-search.js").read_text(encoding="utf-8")
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

	def test_dashboard_currency_guard_remains_active(self) -> None:
		code = (APP_ROOT / "public/js/nexora_quick_flows.js").read_text(encoding="utf-8")
		self.assertIn("escapedCurrencyMarkup", code)
		self.assertIn("normalizeDashboardCurrency", code)
		self.assertIn("node.textContent = match[1].trim()", code)
		self.assertIn("new MutationObserver", code)


if __name__ == "__main__":
	unittest.main()
