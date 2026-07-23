from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class TestCentralLedgerContract(unittest.TestCase):
	def test_catalog_doctypes_and_analytic_dimensions_exist(self):
		for slug in ("nxr_operation_type", "nxr_economic_category"):
			path = ROOT / f"nexora/doctype/{slug}/{slug}.json"
			self.assertTrue(path.is_file(), path)
		effect = json.loads((ROOT / "nexora/doctype/nxr_operation_effect/nxr_operation_effect.json").read_text())
		dimension = next(row for row in effect["fields"] if row["fieldname"] == "dimension")
		self.assertIn("Savings", dimension["options"])
		self.assertIn("Investment", dimension["options"])

	def test_catalog_adapter_uses_existing_transactional_kernel(self):
		text = (ROOT / "financial/analytics.py").read_text()
		self.assertIn("from nexora.financial.operations import execute", text)
		self.assertNotIn("CC Material Ledger", text)
		self.assertIn("execute_central_operation", text)

	def test_internal_transfer_uses_allocation_roles_and_no_second_ledger(self):
		allocation = json.loads((ROOT / "nexora/doctype/nxr_fund_allocation/nxr_fund_allocation.json").read_text())
		self.assertTrue(any(row["fieldname"] == "allocation_role" for row in allocation["fields"]))
		for path in (ROOT / "financial").glob("*.py"):
			self.assertNotIn("CC Material Ledger", path.read_text(), path)


	def test_referenced_corrections_and_advance_guards_are_server_side(self):
		references = (ROOT / "financial/references.py").read_text()
		rules = (ROOT / "financial/reference_rules.py").read_text()
		for token in (
			"derive_reference_effects",
			"validate_return_allocations",
			"_executed_reference_count",
			"ADVANCE_SETTLEMENT",
			"DOCUMENT_SUBSTITUTION",
		):
			self.assertIn(token, references)
		self.assertIn("SEGREGATED_OPERATION_CODES", rules)
		self.assertIn("bounded_reference_amount", rules)

	def test_ui_calls_real_central_ledger_services(self):
		text = (ROOT / "nexora/page/nexora_finance/nexora_finance.js").read_text()
		self.assertIn("preview_central_operation", text)
		self.assertIn("execute_central_operation", text)
		self.assertIn("list_central_operations", text)


if __name__ == "__main__":
	unittest.main()
