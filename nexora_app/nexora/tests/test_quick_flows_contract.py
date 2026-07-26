from __future__ import annotations

import pathlib
import unittest

import nexora


APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestQuickFlowsContract(unittest.TestCase):
	def test_guard_is_loaded_after_primary_product_script(self) -> None:
		hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
		primary = hooks.index('/assets/nexora/js/nexora.js')
		guard = hooks.index('/assets/nexora/js/nexora_quick_flows.js')
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

	def test_capture_guard_prevents_obsolete_dialog_from_running(self) -> None:
		code = (APP_ROOT / "public/js/nexora_quick_flows.js").read_text(encoding="utf-8")
		self.assertIn('event.target?.closest?.(".nxr-quick-expense")', code)
		self.assertIn("event.stopImmediatePropagation()", code)
		self.assertIn("window.nexora.openExpenseDialog = openExpenseDialog", code)


if __name__ == "__main__":
	unittest.main()
