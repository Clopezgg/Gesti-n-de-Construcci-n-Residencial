from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "reporting": ROOT / "reporting.py",
    "weekly": ROOT / "weekly.py",
    "executive": ROOT / "executive.py",
}


class FundingConsumersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sources = {name: path.read_text(encoding="utf-8") for name, path in FILES.items()}

    def test_financial_consumers_use_canonical_received_amount(self) -> None:
        for name, source in self.sources.items():
            with self.subTest(module=name):
                self.assertIn("recognized_funding_amount", source)

    def test_reporting_and_weekly_load_reconciliation_state(self) -> None:
        for name in ("reporting", "weekly"):
            with self.subTest(module=name):
                self.assertIn('"reconciliation_status"', self.sources[name])

    def test_ad_hoc_cancelled_filter_is_removed(self) -> None:
        legacy = 'not in {"cancelled", "rejected"}'
        for name, source in self.sources.items():
            with self.subTest(module=name):
                self.assertNotIn(legacy, source)

    def test_executive_income_chart_uses_recognized_net_amount(self) -> None:
        source = self.sources["executive"]
        self.assertIn("recognized_incomes", source)
        self.assertIn('"recognized_amount_hnl": recognized_amount', source)
        self.assertIn('_category_totals(recognized_incomes, "transaction_channel", "recognized_amount_hnl")', source)


if __name__ == "__main__":
    unittest.main()
