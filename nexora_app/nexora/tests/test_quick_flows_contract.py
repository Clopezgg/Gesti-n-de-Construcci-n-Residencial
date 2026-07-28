from __future__ import annotations

import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestQuickFlowsContract(unittest.TestCase):
	def test_guard_is_loaded_after_primary_product_script(self) -> None:
		hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
		primary = hooks.index("/assets/nexora/js/nexora.js")
		guard = hooks.index("/assets/nexora/js/nexora_quick_flows.js")
		self.assertLess(primary, guard)

	def test_quick_expense_matches_backend_profile_requirements(self) -> None:
		code = (APP_ROOT / "public/js/nexora_quick_flows.js").read_text(encoding="utf-8")
		self.assertIn('operation_code: "CONSTRUCTION_PAYMENT"', code)
		self.assertIn('["CONSTRUCTION_MATERIALS", "CONSTRUCTION_LABOR"]', code)
		self.assertIn('fieldname: "cost_center"', code)
		self.assertIn('fieldname: "beneficiary"', code)
		self.assertGreaterEqual(code.count("reqd: 1"), 7)
		self.assertIn('beneficiary_doctype: "NXR Entity"', code)
		self.assertIn("preview_central_operation", code)
		self.assertIn("execute_central_operation", code)
		self.assertIn("preview_hash", code)
		self.assertIn("idempotency_key: uuid()", code)

	def test_fund_selector_uses_autocomplete_instead_of_native_select(self) -> None:
		code = (APP_ROOT / "public/js/nexora_quick_flows.js").read_text(encoding="utf-8")
		self.assertIn('fieldname: "source"', code)
		self.assertIn('fieldtype: "Autocomplete"', code)
		self.assertNotIn(
			'fieldname: "source", label: __("Fondo que pagará"), fieldtype: "Select"',
			code,
		)
		self.assertIn("sourceControl.set_data(options)", code)
		self.assertIn('sourceControl.$input?.prop("disabled", loading || !options.length)', code)
		self.assertIn('dialog.get_primary_btn()?.prop("disabled", !enabled)', code)

	def test_fund_selector_has_positive_empty_and_error_states(self) -> None:
		code = (APP_ROOT / "public/js/nexora_quick_flows.js").read_text(encoding="utf-8")
		self.assertIn("Cargando fondos…", code)
		self.assertIn("No hay fondos disponibles para este proyecto", code)
		self.assertIn("No se pudieron cargar los fondos", code)
		self.assertIn("row.available_hnl", code)
		self.assertIn("row.balance_hnl", code)
		self.assertIn("row.reserved_hnl", code)

	def test_fund_selector_rejects_typed_or_stale_source(self) -> None:
		code = (APP_ROOT / "public/js/nexora_quick_flows.js").read_text(encoding="utf-8")
		self.assertIn("dialog.nexoraAvailableSources = new Set", code)
		self.assertIn("dialog.nexoraAvailableSources?.has(source)", code)
		self.assertIn(
			"Seleccione un fondo válido con saldo disponible antes de guardar el gasto.",
			code,
		)

	def test_capture_guard_prevents_obsolete_dialog_from_running(self) -> None:
		code = (APP_ROOT / "public/js/nexora_quick_flows.js").read_text(encoding="utf-8")
		self.assertIn('event.target?.closest?.(".nxr-quick-expense")', code)
		self.assertIn("event.stopImmediatePropagation()", code)
		self.assertIn("window.nexora.openExpenseDialog = openExpenseDialog", code)
		self.assertIn("return dialog;", code)

	def test_dashboard_currency_guard_removes_escaped_formatter_markup(self) -> None:
		code = (APP_ROOT / "public/js/nexora_quick_flows.js").read_text(encoding="utf-8")
		self.assertIn("escapedCurrencyMarkup", code)
		self.assertIn("normalizeDashboardCurrency", code)
		self.assertIn("#page-nexora-dashboard [data-currency]", code)
		self.assertIn(".nxr-pending-total", code)
		self.assertIn("new MutationObserver", code)
		self.assertIn("node.textContent = match[1].trim()", code)


if __name__ == "__main__":
	unittest.main()
