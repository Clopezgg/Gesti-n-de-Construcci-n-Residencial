from __future__ import annotations

import json
import unittest
from pathlib import Path

DEFINITIONS = Path(__file__).resolve().parents[1] / "runtime" / "definitions_03.json"
EXPENSE_RULES = Path(__file__).resolve().parents[1] / "expenses.py"


class ExpenseStatusSchemaTest(unittest.TestCase):
	def test_operational_status_accepts_current_and_historical_values(self) -> None:
		definitions = json.loads(DEFINITIONS.read_text(encoding="utf-8"))
		expense = next(row for row in definitions if row.get("name") == "CC Expense Control")
		status = next(row for row in expense["fields"] if row.get("fieldname") == "status")
		self.assertEqual(
			status["options"].splitlines(),
			["pending", "active", "cancelled", "paid", "verified", "missing_receipt"],
		)

	def test_controller_only_writes_values_allowed_by_schema(self) -> None:
		rules = EXPENSE_RULES.read_text(encoding="utf-8")
		self.assertIn('doc.status = "cancelled"', rules)
		self.assertIn('else "pending"', rules)
		self.assertIn('else "active"', rules)


if __name__ == "__main__":
	unittest.main()
