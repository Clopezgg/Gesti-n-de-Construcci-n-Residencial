from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "business_rules.py"
SPEC = importlib.util.spec_from_file_location("cc_business_rules", MODULE)
RULES = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(RULES)


class BusinessRulesTest(unittest.TestCase):
    def test_unknown_historical_expense_is_never_assumed_paid(self):
        result = RULES.normalize_expense_state("active", 217_900, 0)
        self.assertEqual(result["payment_status"], "draft")
        self.assertEqual(result["paid"], 0)
        self.assertEqual(result["balance"], 217_900)

    def test_paid_and_partial_expenses_reconcile_cash_and_balance(self):
        paid = RULES.normalize_expense_state("paid", 1_000, 0)
        partial = RULES.normalize_expense_state("partially_paid", 1_000, 350)
        self.assertEqual((paid["paid"], paid["balance"]), (1_000, 0))
        self.assertEqual((partial["paid"], partial["balance"]), (350, 650))
        self.assertEqual(RULES.expense_amounts(1_000, "paid", "paid", 0, 0), (1_000, 1_000, 0))
        self.assertEqual(RULES.expense_amounts(1_000, "partially_paid", "paid", 350, 650), (1_000, 350, 650))

    def test_cancelled_expense_does_not_affect_cost_or_cash(self):
        self.assertEqual(RULES.expense_amounts(800, "cancelled", "cancelled", 800, 0), (0, 0, 0))

    def test_income_channels_are_canonical_and_unknown_is_other(self):
        self.assertEqual(RULES.normalize_income_channel("Remesa"), "remittance")
        self.assertEqual(RULES.normalize_income_channel("Depósito"), "deposit")
        self.assertEqual(RULES.normalize_income_channel("Transferencia"), "transfer")
        self.assertEqual(RULES.normalize_income_channel("Efectivo"), "cash")
        self.assertEqual(RULES.normalize_income_channel("cripto"), "other")


if __name__ == "__main__":
    unittest.main()
