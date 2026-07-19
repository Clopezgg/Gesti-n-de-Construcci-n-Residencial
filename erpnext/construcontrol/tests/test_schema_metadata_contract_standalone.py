from __future__ import annotations

import ast
import unittest
from pathlib import Path

RUNTIME_SMOKE = Path(__file__).with_name("runtime_smoke.py")


class SchemaMetadataContractTest(unittest.TestCase):
	@classmethod
	def setUpClass(cls) -> None:
		cls.source = RUNTIME_SMOKE.read_text(encoding="utf-8")
		cls.tree = ast.parse(cls.source)

	def test_runtime_checks_standard_and_custom_field_collisions(self) -> None:
		self.assertIn('"DocField"', self.source)
		self.assertIn('"Custom Field"', self.source)
		self.assertIn("standard_fields.intersection(custom_names)", self.source)
		self.assertIn("Counter(custom_names)", self.source)

	def test_runtime_verifies_recorded_contract_sha(self) -> None:
		self.assertIn("validate_runtime_contract_or_raise", self.source)
		self.assertIn('"runtime_contract_sha256"', self.source)
		self.assertIn('recorded_sha == report["sha256"]', self.source)

	def test_schema_check_runs_before_business_crud(self) -> None:
		run_function = next(
			node for node in self.tree.body if isinstance(node, ast.FunctionDef) and node.name == "run"
		)
		calls = [
			node.func.id
			for node in ast.walk(run_function)
			if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
		]
		self.assertLess(calls.index("_verify_schema_metadata"), calls.index("_ensure_test_company"))


if __name__ == "__main__":
	unittest.main()
