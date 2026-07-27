from __future__ import annotations

import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestReportExportGuardContract(unittest.TestCase):
	def test_export_endpoint_is_overridden_by_size_guard(self) -> None:
		hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
		self.assertIn(
			'"nexora.reports.service.export_report": "nexora.reports.safe_export.export_report"',
			hooks,
		)

	def test_paginated_exports_are_rejected_instead_of_truncated(self) -> None:
		code = (APP_ROOT / "reports/safe_export.py").read_text(encoding="utf-8")
		for marker in (
			'"FI01": get_source_statement_page',
			'"FI02": get_expense_page',
			'"CO01": get_contract_page',
			'"page_size": 1',
			"total > EXPORT_ROW_LIMIT",
			"supera el límite autorizado",
			"headers, rows = _snapshot_rows(data, code)",
			"make_xlsx",
			"get_pdf",
			'"report_exported"',
		):
			self.assertIn(marker, code)
		self.assertNotIn("canonical_export_report", code)
		self.assertNotIn("rows[:EXPORT_ROW_LIMIT]", code)

	def test_export_uses_filtered_snapshot_and_fi02_query(self) -> None:
		code = (APP_ROOT / "reports/safe_export.py").read_text(encoding="utf-8")
		self.assertIn("from nexora.dashboard.expense_query import get_expense_page", code)
		self.assertIn("from nexora.dashboard.snapshot_query import get_executive_snapshot", code)
		self.assertIn("rows = _collect_pages(get_expense_page, data)", code)

	def test_browser_uses_the_canonical_server_endpoint(self) -> None:
		code = (APP_ROOT / "nexora/page/nexora-reports/nexora-reports.js").read_text(encoding="utf-8")
		self.assertIn("/api/method/nexora.reports.service.export_report", code)
		self.assertNotIn("Exportar CSV", code)
		self.assertNotIn("window.print()", code)


if __name__ == "__main__":
	unittest.main()
