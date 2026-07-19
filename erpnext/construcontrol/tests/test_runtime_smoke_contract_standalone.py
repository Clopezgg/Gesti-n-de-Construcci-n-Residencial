from __future__ import annotations

import ast
import unittest
from pathlib import Path

RUNTIME_SMOKE = Path(__file__).with_name("runtime_smoke.py")


class RuntimeSmokeContractTest(unittest.TestCase):
	def test_project_fixtures_include_a_real_company(self) -> None:
		source = RUNTIME_SMOKE.read_text(encoding="utf-8")
		tree = ast.parse(source)
		project_payloads = []
		for node in ast.walk(tree):
			if not isinstance(node, ast.Dict):
				continue
			values = {
				key.value: value
				for key, value in zip(node.keys, node.values, strict=False)
				if isinstance(key, ast.Constant) and isinstance(key.value, str)
			}
			if isinstance(values.get("doctype"), ast.Constant) and values["doctype"].value == "Project":
				project_payloads.append(values)

		self.assertEqual(len(project_payloads), 3)
		for payload in project_payloads:
			self.assertIn("company", payload)
			self.assertIsInstance(payload["company"], ast.Name)
			self.assertEqual(payload["company"].id, "company")

	def test_company_fixture_uses_required_stock_fixture_honduras_and_hnl(self) -> None:
		source = RUNTIME_SMOKE.read_text(encoding="utf-8")
		self.assertIn('frappe.db.exists("Warehouse Type", "Transit")', source)
		self.assertIn('{"doctype": "Warehouse Type", "name": "Transit"}', source)
		self.assertIn('"country": "Honduras"', source)
		self.assertIn('"default_currency": "HNL"', source)


if __name__ == "__main__":
	unittest.main()
