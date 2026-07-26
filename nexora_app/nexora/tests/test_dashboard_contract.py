from __future__ import annotations

import json
import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestDashboardContract(unittest.TestCase):
	def test_dashboard_module_exists(self) -> None:
		init = APP_ROOT / "dashboard/__init__.py"
		self.assertTrue(init.is_file())

	def test_dashboard_service_exists(self) -> None:
		service = APP_ROOT / "dashboard/service.py"
		self.assertTrue(service.is_file())

	def test_search_page_json_exists(self) -> None:
		path = APP_ROOT / "nexora/page/nexora-search/nexora-search.json"
		self.assertTrue(path.is_file())
		payload = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual("nexora-search", payload["page_name"])

	def test_search_page_js_exists(self) -> None:
		path = APP_ROOT / "nexora/page/nexora-search/nexora-search.js"
		self.assertTrue(path.is_file())
		code = path.read_text(encoding="utf-8")
		self.assertIn("frappe.pages", code)

	def test_dashboard_page_json_exists(self) -> None:
		path = APP_ROOT / "nexora/page/nexora-dashboard/nexora-dashboard.json"
		self.assertTrue(path.is_file())
		payload = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual("nexora-dashboard", payload["page_name"])

	def test_dashboard_page_js_exists(self) -> None:
		path = APP_ROOT / "nexora/page/nexora-dashboard/nexora-dashboard.js"
		self.assertTrue(path.is_file())
		code = path.read_text(encoding="utf-8")
		self.assertIn("frappe.pages", code)

	def test_dashboard_keeps_project_control_reference(self) -> None:
		code = self._dashboard_code()
		self.assertIn("const projectControl = page.add_field", code)
		self.assertIn("projectControl.get_value()", code)
		self.assertNotIn("controls.project.get_value()", code)

	def test_dashboard_exposes_direct_income_and_expense_actions(self) -> None:
		code = self._dashboard_code()
		self.assertIn('data-operation="Inflow"', code)
		self.assertIn('data-operation="Outflow"', code)
		self.assertIn("frappe.route_options", code)
		self.assertIn('operation_type: operationType', code)

	def test_dashboard_translates_technical_operation_values(self) -> None:
		code = self._dashboard_code()
		self.assertIn('Inflow: __("Ingreso")', code)
		self.assertIn('Outflow: __("Egreso")', code)
		self.assertIn('Draft: __("Borrador")', code)
		self.assertIn('Executed: __("Ejecutado")', code)

	def test_dashboard_handles_loading_failures(self) -> None:
		code = self._dashboard_code()
		self.assertIn("try {", code)
		self.assertIn("catch (error)", code)
		self.assertIn('title: __("Dashboard no disponible")', code)

	def test_service_has_whitelisted_functions(self) -> None:
		path = APP_ROOT / "dashboard/service.py"
		code = path.read_text(encoding="utf-8")
		self.assertIn("@frappe.whitelist", code)
		self.assertIn("def universal_search", code)
		self.assertIn("def get_dashboard_summary", code)

	def test_service_imports_permissions(self) -> None:
		path = APP_ROOT / "dashboard/service.py"
		code = path.read_text(encoding="utf-8")
		self.assertIn("require_action", code)

	def test_workspace_has_dashboard_and_search_shortcuts(self) -> None:
		path = APP_ROOT / "nexora/workspace/nexora/nexora.json"
		payload = json.loads(path.read_text(encoding="utf-8"))
		shortcuts = [s["label"] for s in payload.get("shortcuts", [])]
		self.assertIn("Dashboard NEXORA", shortcuts)
		self.assertIn("Buscador universal", shortcuts)

	@staticmethod
	def _dashboard_code() -> str:
		path = APP_ROOT / "nexora/page/nexora-dashboard/nexora-dashboard.js"
		return path.read_text(encoding="utf-8")
