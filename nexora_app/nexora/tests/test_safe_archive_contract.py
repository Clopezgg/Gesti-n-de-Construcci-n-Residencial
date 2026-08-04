from __future__ import annotations

import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestSafeArchiveContract(unittest.TestCase):
	def test_fund_source_cancellation_is_compensatory_and_audited(self) -> None:
		code = (APP_ROOT / "financial/sources.py").read_text(encoding="utf-8")
		for marker in (
			'require_action("cancel_source")',
			"FOR UPDATE",
			'"effect_type": "Reversed"',
			'"is_reversal": 1',
			'"reverses_effect": initial_effect.name',
			'original_operation.status = "Compensated Total"',
			'audit("fund_source_cancelled"',
			"rollback(point)",
		):
			self.assertIn(marker, code)
		self.assertNotIn("delete_doc", code)

	def test_fi01_exposes_safe_cancellation_without_deletion(self) -> None:
		code = (APP_ROOT / "nexora/page/nexora_reports/nexora_reports.js").read_text(encoding="utf-8")
		for marker in (
			"data-cancel-source",
			"nexora.financial.sources.cancel_fund_source",
			"Anular mediante compensación",
			"no elimina el registro",
			'$(document).trigger("nexora:data-changed")',
		):
			self.assertIn(marker, code)

	def test_saved_report_archive_is_owner_scoped_idempotent_and_audited(self) -> None:
		code = (APP_ROOT / "reports/actions.py").read_text(encoding="utf-8")
		for marker in (
			'@frappe.whitelist(methods=["POST"])',
			"start_idempotency",
			"FOR UPDATE",
			"doc.owner_user != frappe.session.user",
			'doc.status = "Archived"',
			"with service_write()",
			'"saved_report_archived"',
			"complete_idempotency",
			"rollback(point)",
		):
			self.assertIn(marker, code)
		self.assertNotIn("delete_doc", code)

	def test_saved_report_archive_has_real_interface_and_is_loaded(self) -> None:
		actions = (APP_ROOT / "public/js/nexora_report_actions.js").read_text(encoding="utf-8")
		hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
		for marker in (
			"data-archive-saved",
			"nexora.reports.actions.archive_saved_report",
			"archive-saved-report-${reportName}",
			"conservará su número, filtros y auditoría",
		):
			self.assertIn(marker, actions)
		self.assertIn("/assets/nexora/js/nexora_report_actions.js", hooks)

	def test_saved_reports_cannot_be_hard_deleted(self) -> None:
		controller = (APP_ROOT / "nexora/doctype/nxr_saved_report/nxr_saved_report.py").read_text(
			encoding="utf-8"
		)
		self.assertIn("def on_trash", controller)
		self.assertIn("no se eliminan; deben archivarse", controller)


if __name__ == "__main__":
	unittest.main()
