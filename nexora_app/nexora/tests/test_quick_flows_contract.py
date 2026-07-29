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
			"data-submitting",
			"aria-busy",
			"stopImmediatePropagation",
		):
			self.assertIn(marker, code)

	def test_guided_expense_preserves_server_preview_and_multifund_ui(self) -> None:
		quick = (APP_ROOT / "public/js/nexora_quick_flows.js").read_text(encoding="utf-8")
		page = (
			APP_ROOT / "nexora/page/nexora_operations/nexora_operations.js"
		).read_text(encoding="utf-8")
		self.assertIn("saldo anterior, importe afectado y saldo resultante", quick)
		self.assertIn('data-detail-tab="funds"', page)
		self.assertIn("allocations()", page)
		self.assertIn("preview_operational_movement", page)
		self.assertIn("execute_operational_movement", page)
		self.assertIn("preview_hash", page)
		self.assertIn("idempotency_key", page)

	def test_dashboard_currency_guard_remains_active(self) -> None:
		code = (APP_ROOT / "public/js/nexora_quick_flows.js").read_text(encoding="utf-8")
		self.assertIn("escapedCurrencyMarkup", code)
		self.assertIn("normalizeDashboardCurrency", code)
		self.assertIn("node.textContent = match[1].trim()", code)
		self.assertIn("new MutationObserver", code)


if __name__ == "__main__":
	unittest.main()
