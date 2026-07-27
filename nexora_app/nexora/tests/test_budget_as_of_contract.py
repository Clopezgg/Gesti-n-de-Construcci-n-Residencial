from __future__ import annotations

import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestBudgetAsOfContract(unittest.TestCase):
	def test_budget_snapshot_uses_the_applicable_version_and_ledger_effects(self) -> None:
		code = (APP_ROOT / "close/as_of.py").read_text(encoding="utf-8")
		for marker in (
			"def budget_snapshot_as_of",
			"newer.effective_date<=%(period_end)s",
			"e.dimension='Budget'",
			"o.operation_date<=%(period_end)s",
			"economic_category=%(economic_category)s",
			"cost_center=%(cost_center)s",
			'"lines": lines',
			'"utilization_percent"',
		):
			self.assertIn(marker, code)

	def test_close_helper_can_return_summary_without_duplicate_financial_logic(self) -> None:
		code = (APP_ROOT / "close/as_of.py").read_text(encoding="utf-8")
		self.assertIn('result.pop("lines", None)', code)
		self.assertIn("budget_totals_as_of", code)
		service = (APP_ROOT / "close/service.py").read_text(encoding="utf-8")
		self.assertNotIn("budget_totals_as_of", service)
		self.assertIn('budget_totals = dict(snapshot.get("budgets", {}))', service)

	def test_filtered_snapshot_builds_historical_budget_and_pending_values_directly(self) -> None:
		code = (APP_ROOT / "dashboard/snapshot_query.py").read_text(encoding="utf-8")
		for marker in (
			"budget_snapshot_as_of",
			"period_is_filtered",
			'query_data = {**data, "from_date": start, "to_date": end}',
			'pending = pending_commitments({**query_data',
			"budgets = _historical_budgets(query_data, project, end)",
			'"budget_kpis_filtered": period_is_filtered',
			'data.get("to_date") or frappe.utils.today()',
			"build_operational_sections",
		):
			self.assertIn(marker, code)
		self.assertNotIn('snapshot["budgets"] = _historical_budgets', code)
		self.assertNotIn("get_dashboard_summary", code)


if __name__ == "__main__":
	unittest.main()
