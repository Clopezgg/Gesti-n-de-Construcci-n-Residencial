from __future__ import annotations

import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestReportFilterUIContract(unittest.TestCase):
	def test_report_center_exposes_financial_and_contract_filters(self) -> None:
		code = (APP_ROOT / "nexora/page/nexora_reports/nexora_reports.js").read_text(encoding="utf-8")
		for marker in (
			'fieldname: "project"',
			'fieldname: "from_date"',
			'fieldname: "to_date"',
			'fieldname: "source"',
			'fieldname: "economic_category"',
			'fieldname: "cost_center"',
			'fieldname: "entity"',
			'fieldname: "payment_method"',
			'fieldname: "contractor"',
			'fieldname: "contract_status"',
		):
			self.assertIn(marker, code)

	def test_all_filters_are_sent_to_preview_detail_export_and_saved_reports(self) -> None:
		code = (APP_ROOT / "nexora/page/nexora_reports/nexora_reports.js").read_text(encoding="utf-8")
		for marker in (
			"cost_center: controls.cost_center.get_value() || null",
			"payment_method: controls.payment_method.get_value() || null",
			"contract_status: controls.contract_status.get_value() || null",
			"args: { payload: payload() }",
			"const exportPayload = { ...payload(), report_code: activeView, format }",
			"filters: payload()",
			"Object.entries(saved.filters || {})",
		):
			self.assertIn(marker, code)

	def test_interface_discloses_active_filter_count(self) -> None:
		code = (APP_ROOT / "nexora/page/nexora_reports/nexora_reports.js").read_text(encoding="utf-8")
		self.assertIn("snapshot.filter_context?.active", code)
		self.assertIn("filtro(s) activo(s)", code)


if __name__ == "__main__":
	unittest.main()
