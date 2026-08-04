from __future__ import annotations

import json
import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestReportsContract(unittest.TestCase):
	def test_reports_module_exists(self) -> None:
		init = APP_ROOT / "reports/__init__.py"
		self.assertTrue(init.is_file())

	def test_reports_core_exists(self) -> None:
		core = APP_ROOT / "reports/core.py"
		self.assertTrue(core.is_file())

	def test_reports_service_exists(self) -> None:
		service = APP_ROOT / "reports/service.py"
		self.assertTrue(service.is_file())

	def test_reports_page_json_exists(self) -> None:
		path = APP_ROOT / "nexora/page/nexora_reports/nexora_reports.json"
		self.assertTrue(path.is_file())
		payload = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual("nexora-reports", payload["page_name"])

	def test_reports_page_js_exists(self) -> None:
		path = APP_ROOT / "nexora/page/nexora_reports/nexora_reports.js"
		self.assertTrue(path.is_file())
		code = path.read_text(encoding="utf-8")
		self.assertIn("frappe.pages", code)

	def test_service_has_report_functions(self) -> None:
		path = APP_ROOT / "reports/service.py"
		code = path.read_text(encoding="utf-8")
		self.assertIn("@frappe.whitelist", code)
		self.assertIn("def get_source_statement", code)
		self.assertIn("def get_entity_statement", code)
		self.assertIn("def get_contract_statement", code)
		self.assertIn("def get_financial_report", code)
		self.assertIn("def get_cost_report", code)
		self.assertIn("def reconcile_totals", code)

	def test_service_uses_require_action(self) -> None:
		path = APP_ROOT / "reports/service.py"
		code = path.read_text(encoding="utf-8")
		self.assertIn("require_action", code)
