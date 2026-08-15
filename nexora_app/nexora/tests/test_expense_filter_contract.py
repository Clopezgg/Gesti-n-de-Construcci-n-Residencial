from __future__ import annotations

import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestExpenseFilterContract(unittest.TestCase):
	def test_fi02_filters_the_effect_rows_before_aggregation(self) -> None:
		code = (APP_ROOT / "dashboard/expense_query.py").read_text(encoding="utf-8")
		for marker in (
			"INNER JOIN `tabNXR Operation Effect` fx",
			"fx.dimension='Funds'",
			"fx.amount_hnl<0",
			"COALESCE(fx.is_reversal,0)=0",
			"fx.fund_source=%(source)s",
			"COALESCE(fx.economic_category,o.economic_category)=%(economic_category)s",
			"COALESCE(fx.cost_center,o.cost_center)=%(cost_center)s",
			"COALESCE(SUM(-fx.amount_hnl),0) amount_hnl",
			"COUNT(DISTINCT o.name)",
		):
			self.assertIn(marker, code)

	def test_endpoint_and_export_share_the_same_fi02_query(self) -> None:
		hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
		export = (APP_ROOT / "reports/safe_export.py").read_text(encoding="utf-8")
		self.assertIn('"nexora.dashboard.executive.get_expense_page":', hooks)
		self.assertIn("nexora.dashboard.expense_query.get_expense_page", hooks)
		self.assertIn("from nexora.dashboard.expense_query import get_expense_page", export)

	def test_query_enforces_financial_details_and_project_scope(self) -> None:
		code = (APP_ROOT / "dashboard/expense_query.py").read_text(encoding="utf-8")
		self.assertIn('require_action("view_financial_details")', code)
		self.assertIn('require_project_access(project, action="view_financial_details")', code)
		self.assertIn("MAX_PAGE_SIZE = 100", code)


if __name__ == "__main__":
	unittest.main()
