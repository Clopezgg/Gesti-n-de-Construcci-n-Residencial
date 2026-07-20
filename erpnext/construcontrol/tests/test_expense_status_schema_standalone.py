from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

DEFINITIONS = Path(__file__).resolve().parents[1] / "runtime" / "definitions_03.json"
EXPENSE_RULES = Path(__file__).resolve().parents[1] / "expenses.py"


def string_literals(node: ast.AST) -> set[str]:
    return {
        child.value
        for child in ast.walk(node)
        if isinstance(child, ast.Constant) and isinstance(child.value, str)
    }


class ExpenseStatusSchemaTest(unittest.TestCase):
    def setUp(self) -> None:
        definitions = json.loads(DEFINITIONS.read_text(encoding="utf-8"))
        expense = next(row for row in definitions if row.get("name") == "CC Expense Control")
        status = next(row for row in expense["fields"] if row.get("fieldname") == "status")
        self.allowed = set(status["options"].splitlines())

    def test_operational_status_accepts_current_and_historical_values(self) -> None:
        self.assertEqual(
            self.allowed,
            {"pending", "active", "cancelled", "paid", "verified", "missing_receipt"},
        )

    def test_controller_only_writes_values_allowed_by_schema(self) -> None:
        tree = ast.parse(EXPENSE_RULES.read_text(encoding="utf-8"))
        assigned: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if not any(
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "doc"
                and target.attr == "status"
                for target in targets
            ):
                continue
            assigned.update(string_literals(node.value))
        self.assertTrue({"pending", "active", "cancelled"}.issubset(assigned))
        self.assertTrue(assigned.issubset(self.allowed), assigned - self.allowed)


if __name__ == "__main__":
    unittest.main()
