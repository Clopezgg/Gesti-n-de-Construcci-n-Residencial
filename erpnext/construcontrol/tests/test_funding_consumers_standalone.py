from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTING_SUMMARY = ROOT / "reporting_summary.py"
WEEKLY_IMPLEMENTATION = ROOT / "weekly_impl.py"
EXECUTIVE_IMPLEMENTATION = ROOT / "executive_impl.py"


class FundingConsumersTest(unittest.TestCase):
	@classmethod
	def setUpClass(cls) -> None:
		cls.reporting = REPORTING_SUMMARY.read_text(encoding="utf-8")
		cls.weekly = WEEKLY_IMPLEMENTATION.read_text(encoding="utf-8")
		cls.executive = EXECUTIVE_IMPLEMENTATION.read_text(encoding="utf-8")

	def test_financial_consumers_use_canonical_received_amount(self) -> None:
		for name, source in (
			("reporting", self.reporting),
			("weekly", self.weekly),
		):
			with self.subTest(module=name):
				self.assertIn("recognized_funding_amount", source)

	def test_reporting_and_weekly_load_reconciliation_state(self) -> None:
		for name, source in (
			("reporting", self.reporting),
			("weekly", self.weekly),
		):
			with self.subTest(module=name):
				self.assertIn('"reconciliation_status"', source)

	def test_ad_hoc_cancelled_filter_is_removed(self) -> None:
		legacy = 'not in {"cancelled", "rejected"}'
		for name, source in (
			("reporting", self.reporting),
			("weekly", self.weekly),
			("executive", self.executive),
		):
			with self.subTest(module=name):
				self.assertNotIn(legacy, source)

	def test_executive_income_chart_uses_canonical_summary_channels(self) -> None:
		self.assertIn("get_reporting_summary", self.executive)
		self.assertIn('summary.get("income_channels", [])', self.executive)
		self.assertNotIn('"amount_hnl": row.get("amount_hnl")', self.executive)


if __name__ == "__main__":
	unittest.main()
