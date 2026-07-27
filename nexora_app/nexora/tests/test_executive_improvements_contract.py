from __future__ import annotations

import json
import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestExecutiveImprovementsContract(unittest.TestCase):
	def test_analytics_uses_effect_ledger_and_pagination(self) -> None:
		code = (APP_ROOT / "dashboard/executive.py").read_text(encoding="utf-8")
		for marker in (
			"tabNXR Operation Effect",
			"opening_funds_hnl",
			"closing_funds_hnl",
			"transfer_in_hnl",
			"transfer_out_hnl",
			"MAX_PAGE_SIZE = 100",
			"get_source_movement_page",
			"critical_inventory",
		):
			self.assertIn(marker, code)
		self.assertNotIn("limit_page_length=10000", code)
		self.assertNotIn("received - current_balance", code)

	def test_dashboard_keeps_certified_contract_and_premium_panels(self) -> None:
		code = (APP_ROOT / "nexora/page/nexora-dashboard/nexora-dashboard.js").read_text(
			encoding="utf-8"
		)
		for marker in (
			"nxr-dashboard-shell",
			"nxr-dashboard-recent-rows",
			"nxr-evidence-tile",
			"Inventario crítico",
			"Fondos y remesas",
			"nexora:data-changed",
			'[data-route]:not([data-action])',
		):
			self.assertIn(marker, code)
		self.assertNotIn('data-route="nexora-finance" data-action="expense"', code)

	def test_exports_are_server_authorized_excel_and_pdf(self) -> None:
		service = (APP_ROOT / "reports/service.py").read_text(encoding="utf-8")
		page = (APP_ROOT / "nexora/page/nexora-reports/nexora-reports.js").read_text(
			encoding="utf-8"
		)
		for marker in ('require_action("export_reports")', "make_xlsx", "get_pdf", "report_exported"):
			self.assertIn(marker, service)
		self.assertNotIn("window.print()", page)
		self.assertNotIn("Exportar CSV", page)
		self.assertNotIn("new Blob", page)

	def test_weekly_close_is_canonical_and_immutable(self) -> None:
		model = json.loads(
			(APP_ROOT / "nexora/doctype/nxr_weekly_close/nxr_weekly_close.json").read_text(
				encoding="utf-8"
			)
		)
		fields = {field["fieldname"]: field for field in model["fields"]}
		self.assertEqual("hash", model["autoname"])
		for fieldname in (
			"document_number",
			"period_key",
			"idempotency_key",
			"payload_hash",
			"correlation_id",
			"snapshot_hash",
			"engine_version",
			"correction_of",
		):
			self.assertIn(fieldname, fields)
		controller = (
			APP_ROOT / "nexora/doctype/nxr_weekly_close/nxr_weekly_close.py"
		).read_text(encoding="utf-8")
		service = (APP_ROOT / "close/service.py").read_text(encoding="utf-8")
		self.assertIn("require_service_write", controller)
		for marker in (
			"start_idempotency",
			"issue_document_number",
			"savepoint",
			"rollback",
			"audit",
			"DuplicateEntryError",
		):
			self.assertIn(marker, service)

	def test_workspace_exposes_reporting_and_closing(self) -> None:
		workspace = json.loads(
			(APP_ROOT / "nexora/workspace/nexora/nexora.json").read_text(encoding="utf-8")
		)
		labels = {row["label"] for row in workspace["shortcuts"]}
		self.assertIn("Centro de reportes", labels)
		self.assertIn("Cierre semanal", labels)
		self.assertIn("Reportes guardados", labels)


if __name__ == "__main__":
	unittest.main()
