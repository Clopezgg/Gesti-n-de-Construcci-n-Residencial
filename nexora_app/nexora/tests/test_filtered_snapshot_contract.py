from __future__ import annotations

import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestFilteredSnapshotContract(unittest.TestCase):
	def test_whitelisted_snapshot_is_replaced_by_filter_adapter(self) -> None:
		hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
		self.assertIn(
			'"nexora.dashboard.executive.get_executive_snapshot": (',
			hooks,
		)
		self.assertIn(
			'"nexora.dashboard.snapshot_query.get_executive_snapshot"',
			hooks,
		)

	def test_snapshot_composes_existing_analytics_without_repeating_base_snapshot(self) -> None:
		code = (APP_ROOT / "dashboard/snapshot_query.py").read_text(encoding="utf-8")
		for marker in (
			"get_dashboard_summary",
			"_source_statement",
			"expense_page({**data",
			"_contract_page",
			"contract_totals(data)",
			"expense_breakdowns(data)",
			'"spent_hnl": expenses["summary"]["amount_hnl"]',
		):
			self.assertIn(marker, code)
		self.assertNotIn("canonical_snapshot", code)

	def test_source_contract_and_pending_kpis_respect_filters(self) -> None:
		code = (APP_ROOT / "dashboard/snapshot_query.py").read_text(encoding="utf-8")
		for marker in (
			"if source:",
			'"received_hnl": source_totals["received_hnl"]',
			'"cash_available_hnl": source_totals["closing_available_hnl"]',
			'"paid_hnl": contracts["paid_hnl"]',
			"pending = pending_commitments",
			'"pending_obligations_hnl": number(pending.get("total_hnl"))',
			'"filter_context"',
		):
			self.assertIn(marker, code)

	def test_pending_query_is_ledger_based_and_paginated(self) -> None:
		code = (APP_ROOT / "dashboard/pending_query.py").read_text(encoding="utf-8")
		for marker in (
			"FROM `tabNXR Operation Effect` e",
			"e.dimension='Reserved'",
			"o.operation_date<=%(end)s",
			"e.fund_source=%(source)s",
			"HAVING amount_hnl>0",
			"MAX_PAGE_SIZE = 100",
		):
			self.assertIn(marker, code)

	def test_contract_totals_apply_the_same_co01_filters(self) -> None:
		code = (APP_ROOT / "dashboard/contract_query.py").read_text(encoding="utf-8")
		for marker in (
			"c.start_date<=%(end)s",
			"c.current_end_date>=%(start)s",
			'("contractor", "c.contractor"',
			'("contract_status", "c.status"',
			"COUNT(*) contract_count",
		):
			self.assertIn(marker, code)


if __name__ == "__main__":
	unittest.main()
