from __future__ import annotations

import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestCanonicalReportViewsContract(unittest.TestCase):
	def test_public_report_methods_are_overridden_by_filtered_views(self) -> None:
		hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
		for marker in (
			'"nexora.reports.service.get_financial_report": (',
			'"nexora.reports.canonical_views.get_financial_report"',
			'"nexora.reports.service.get_cost_report": "nexora.reports.canonical_views.get_cost_report"',
			'"nexora.reports.service.reconcile_totals": "nexora.reports.canonical_views.reconcile_totals"',
		):
			self.assertIn(marker, hooks)

	def test_views_use_filtered_snapshot_and_server_permissions(self) -> None:
		code = (APP_ROOT / "reports/canonical_views.py").read_text(encoding="utf-8")
		for marker in (
			"from nexora.dashboard.snapshot_query import get_executive_snapshot",
			'require_action("view_reports")',
			'require_action("view_financial_details")',
			"require_project_access",
			'"filter_context": snapshot.get("filter_context", {})',
			'"outflows": snapshot.get("executive", {}).get("spent_hnl", 0)',
		):
			self.assertIn(marker, code)


if __name__ == "__main__":
	unittest.main()
