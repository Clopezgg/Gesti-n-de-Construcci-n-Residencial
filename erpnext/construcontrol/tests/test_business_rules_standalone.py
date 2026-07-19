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
        self.assertEqual(RULES.expense_amounts(1_000, "paid", "paid", 0, 0, "approved"), (1_000, 1_000, 0))
        self.assertEqual(RULES.expense_amounts(1_000, "partially_paid", "paid", 350, 650, "approved"), (1_000, 350, 650))

    def test_cancelled_and_rejected_expenses_do_not_affect_cost_or_cash(self):
        self.assertEqual(RULES.expense_amounts(800, "cancelled", "cancelled", 800, 0, "approved"), (0, 0, 0))
        self.assertEqual(RULES.expense_amounts(800, "pending_approval", "pending", 0, 800, "rejected"), (0, 0, 0))

    def test_drafts_do_not_become_approved_cost(self):
        self.assertEqual(RULES.expense_amounts(800, "draft", "pending", 0, 800, "draft"), (0, 0, 0))
        self.assertEqual(RULES.expense_amounts(800, "pending_approval", "pending", 0, 800, "pending"), (0, 0, 0))
        self.assertEqual(RULES.expense_amounts(800, "approved", "pending", 0, 800, "approved"), (800, 0, 800))

    def test_income_channels_are_canonical_and_unknown_is_other(self):
        self.assertEqual(RULES.normalize_income_channel("Remesa"), "remittance")
        self.assertEqual(RULES.normalize_income_channel("Depósito"), "deposit")
        self.assertEqual(RULES.normalize_income_channel("Transferencia"), "transfer")
        self.assertEqual(RULES.normalize_income_channel("Efectivo"), "cash")
        self.assertEqual(RULES.normalize_income_channel("cripto"), "other")

    def test_funding_amounts_force_hnl_rate_and_deduct_fees(self):
        self.assertEqual(
            RULES.funding_amounts(1_000, 50, "HNL", 27),
            {
                "gross": 1_000.0,
                "fee": 50.0,
                "net": 950.0,
                "currency": "HNL",
                "exchange_rate": 1.0,
                "net_hnl": 950.0,
            },
        )

    def test_funding_amounts_convert_foreign_currency_after_fee(self):
        result = RULES.funding_amounts(100, 5, "usd", 24.75)
        self.assertEqual(result["currency"], "USD")
        self.assertEqual(result["net"], 95.0)
        self.assertEqual(result["exchange_rate"], 24.75)
        self.assertEqual(result["net_hnl"], 2_351.25)

    def test_funding_amounts_reject_invalid_fee(self):
        with self.assertRaisesRegex(ValueError, "comisión no puede superar"):
            RULES.funding_amounts(100, 101, "HNL", 1)
        with self.assertRaisesRegex(ValueError, "no pueden ser negativos"):
            RULES.funding_amounts(-1, 0, "HNL", 1)

    def test_funding_amounts_require_positive_foreign_rate(self):
        with self.assertRaisesRegex(ValueError, "tipo de cambio debe ser mayor"):
            RULES.funding_amounts(100, 0, "USD", 0)


if __name__ == "__main__":
    unittest.main()
