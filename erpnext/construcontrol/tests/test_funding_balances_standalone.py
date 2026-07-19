from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RULES_PATH = ROOT / "erpnext" / "construcontrol" / "business_rules.py"
CONTROLLERS = ROOT / "erpnext" / "construcontrol" / "controllers.py"
FINANCE = ROOT / "erpnext" / "construcontrol" / "finance.py"

SPEC = importlib.util.spec_from_file_location("cc_funding_rules", RULES_PATH)
RULES = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(RULES)


class FundingBalancesTest(unittest.TestCase):
	def test_reconciliation_drives_terminal_operational_state(self) -> None:
		self.assertEqual(
			RULES.normalize_funding_state("pending", "reconciled"),
			{"status": "received", "reconciliation_status": "reconciled"},
		)
		self.assertEqual(
			RULES.normalize_funding_state("received", "rejected"),
			{"status": "cancelled", "reconciliation_status": "rejected"},
		)

	def test_only_received_non_rejected_funds_become_cash(self) -> None:
		self.assertEqual(RULES.recognized_funding_amount(1_000, "pending", "verified"), 0)
		self.assertEqual(RULES.recognized_funding_amount(1_000, "held", "pending"), 0)
		self.assertEqual(RULES.recognized_funding_amount(1_000, "received", "verified"), 1_000)
		self.assertEqual(RULES.recognized_funding_amount(1_000, "received", "rejected"), 0)

	def test_available_and_projected_balances_are_distinct(self) -> None:
		balances = RULES.funding_balances(1_000, "received", "verified", 250, 300)
		self.assertEqual(balances["received_hnl"], 1_000)
		self.assertEqual(balances["spent_hnl"], 250)
		self.assertEqual(balances["pending_hnl"], 300)
		self.assertEqual(balances["available_hnl"], 750)
		self.assertEqual(balances["projected_hnl"], 450)

	def test_funding_cannot_drop_below_paid_or_committed_expenses(self) -> None:
		with self.assertRaisesRegex(ValueError, "gasto pagado"):
			RULES.funding_balances(200, "received", "verified", 250, 0)
		with self.assertRaisesRegex(ValueError, "gasto comprometido"):
			RULES.funding_balances(500, "received", "verified", 250, 300)

	def test_cancelled_or_held_source_cannot_back_existing_expenses(self) -> None:
		with self.assertRaisesRegex(ValueError, "gasto pagado"):
			RULES.funding_balances(1_000, "cancelled", "rejected", 1, 0)
		with self.assertRaisesRegex(ValueError, "gasto comprometido"):
			RULES.funding_balances(1_000, "held", "pending", 0, 1)

	def test_backend_contract_uses_canonical_funding_balances(self) -> None:
		controllers = CONTROLLERS.read_text(encoding="utf-8")
		finance = FINANCE.read_text(encoding="utf-8")
		self.assertGreaterEqual(controllers.count("funding_balances("), 3)
		self.assertIn("normalize_funding_state", finance)
		self.assertNotIn(
			"projected = fund_amount - other_paid - other_pending - current_recognized",
			controllers,
		)


if __name__ == "__main__":
	unittest.main()
