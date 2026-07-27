from __future__ import annotations

import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestAnalyticsHistoryContract(unittest.TestCase):
	def test_historical_source_pages_exclude_future_sources(self) -> None:
		code = (APP_ROOT / "dashboard/source_query.py").read_text(encoding="utf-8")
		self.assertIn('["source_date", "<=", end]', code)

	def test_reversals_are_reported_once_not_reclassified_as_normal_flow(self) -> None:
		code = (APP_ROOT / "dashboard/source_query.py").read_text(encoding="utf-8")
		self.assertGreaterEqual(code.count("COALESCE(e.is_reversal,0)=0"), 12)
		self.assertIn("COALESCE(e.is_reversal,0)=1", code)

	def test_expense_analytics_uses_canonical_effect_ledger(self) -> None:
		code = (APP_ROOT / "dashboard/expense_query.py").read_text(encoding="utf-8")
		for marker in (
			"INNER JOIN `tabNXR Operation Effect` fx",
			"COUNT(DISTINCT o.name)",
			"fx.dimension='Funds'",
			"fx.amount_hnl<0",
			"COALESCE(fx.is_reversal,0)=0",
			"GROUP_CONCAT(DISTINCT fx.fund_source",
		):
			self.assertIn(marker, code)

	def test_projection_does_not_double_subtract_reserved_obligations(self) -> None:
		code = (APP_ROOT / "dashboard/snapshot_query.py").read_text(encoding="utf-8")
		self.assertIn('"projected_available_hnl": source_totals["closing_available_hnl"]', code)
		self.assertIn('"pending_obligations_hnl": number(pending.get("total_hnl"))', code)
		self.assertIn("evitar doble conteo", code)
		self.assertNotIn(
			'Decimal(str(source_totals["closing_available_hnl"])) - Decimal(str(pending_total))',
			code,
		)

	def test_cancelled_sources_are_not_left_as_unreconciled_alerts(self) -> None:
		code = (APP_ROOT / "dashboard/snapshot_query.py").read_text(encoding="utf-8")
		self.assertIn('"status": ["not in", ["Draft", "Cancelled"]]', code)


if __name__ == "__main__":
	unittest.main()
