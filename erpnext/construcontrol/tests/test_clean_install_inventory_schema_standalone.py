from __future__ import annotations

import ast
import unittest
from pathlib import Path

INSTALL = Path(__file__).resolve().parents[1] / "install.py"


class CleanInstallInventorySchemaContractTest(unittest.TestCase):
	def test_clean_install_invokes_inventory_schema_before_runtime_use(self) -> None:
		tree = ast.parse(INSTALL.read_text(encoding="utf-8"))
		after_migrate = next(
			node
			for node in tree.body
			if isinstance(node, ast.FunctionDef) and node.name == "after_migrate"
		)
		imports = {
			alias.name
			for node in ast.walk(after_migrate)
			if isinstance(node, ast.ImportFrom)
			and node.module == "erpnext.construcontrol.inventory"
			for alias in node.names
		}
		self.assertIn("ensure_inventory_schema", imports)

		calls = [
			node.func.id
			for node in after_migrate.body
			if isinstance(node, ast.Expr)
			and isinstance(node.value, ast.Call)
			and isinstance((node := node.value).func, ast.Name)
		]
		self.assertIn("ensure_inventory_schema", calls)
		self.assertLess(calls.index("ensure_inventory_schema"), calls.index("ensure_quality_schema"))


if __name__ == "__main__":
	unittest.main()
