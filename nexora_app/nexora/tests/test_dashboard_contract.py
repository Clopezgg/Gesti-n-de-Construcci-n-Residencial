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
		self.assertIn('data-action="income"', code)
		self.assertIn('data-action="expense"', code)
		self.assertIn("frappe.route_options", code)
		self.assertIn("nexora_action: action", code)
		self.assertIn("project: projectControl.get_value()", code)

	def test_dashboard_uses_official_product_identity(self) -> None:
		code = self._dashboard_code()
		self.assertIn('title: __("NEXORA")', code)
		self.assertIn("Gestión Integral de Fondos, Proyectos y Operaciones", code)
		self.assertNotIn("NEXORA — Control de obras", code)

	def test_dashboard_translates_technical_operation_values(self) -> None:
		code = self._dashboard_code()
		self.assertIn('Inflow: __("Ingreso")', code)
		self.assertIn('Outflow: __("Gasto")', code)
		self.assertIn('"Internal Transfer": __("Transferencia interna")', code)
		self.assertIn('"Real Return": __("Devolución real")', code)
		self.assertIn('Draft: __("Borrador")', code)
		self.assertIn('Executed: __("Ejecutado")', code)

	def test_dashboard_handles_loading_failures(self) -> None:
		code = self._dashboard_code()
		self.assertIn("try {", code)
		self.assertIn("catch (error)", code)
		self.assertIn('title: __("Dashboard no disponible")', code)

	def test_dashboard_integrates_complete_operational_summary(self) -> None:
		code = self._dashboard_code()
		for marker in (
			"finance.total_available_hnl",
			"finance.total_reserved_hnl",
			"budgets.total_executed_hnl",
			"pending_accounts",
			"progress.physical_percent",
			"nxr-evidence-gallery",
			"nxr-alert-rows",
			"nxr-contract-rows",
		):
			self.assertIn(marker, code)

	def test_dashboard_service_reconciles_against_canonical_effect_ledger(self) -> None:
		path = APP_ROOT / "dashboard/service.py"
		code = path.read_text(encoding="utf-8")
		self.assertIn("source_states", code)
		self.assertIn('"NXR Operation Effect"', code)
		self.assertIn('"Reserved"', code)
		self.assertIn('"Budget"', code)
		self.assertIn('{"Commitment Reserve", "Commitment Release"}', code)
		self.assertIn('"NXR Contract Estimate"', code)
		self.assertIn('"NXR Progress Record"', code)
		self.assertIn('"NXR Evidence"', code)

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

	def test_global_navigation_uses_canonical_nexora_pages(self) -> None:
		code = (APP_ROOT / "public/js/nexora.js").read_text(encoding="utf-8")
		for route in (
			"/app/nexora-dashboard",
			"/app/nexora-finance",
			"/app/nexora-contracts",
			"/app/nexora-suppliers",
			"/app/nexora-evidence",
			"/app/nexora-reports",
		):
			self.assertIn(route, code)
		self.assertIn('frappe.boot?.home_page === "nexora-dashboard"', code)
		self.assertIn("shell.parentElement !== main", code)

	def test_apps_screen_opens_the_dashboard(self) -> None:
		hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
		self.assertIn('"route": "/app/nexora-dashboard"', hooks)

	def test_dashboard_is_the_canonical_desk_home(self) -> None:
		install = (APP_ROOT / "install.py").read_text(encoding="utf-8")
		self.assertIn('NEXORA_HOME_PAGE = "nexora-dashboard"', install)
		self.assertIn('frappe.db.set_default("desktop:home_page", NEXORA_HOME_PAGE)', install)
		self.assertIn("_ensure_nexora_home_page()", install)

	def test_dashboard_styles_cover_mobile_composition(self) -> None:
		css = (APP_ROOT / "public/css/nexora.css").read_text(encoding="utf-8")
		for selector in (
			".nxr-dashboard-shell",
			".nxr-dashboard-welcome",
			".nxr-section-heading",
			".nxr-dashboard-primary-actions",
			".nxr-balance-row",
			".nxr-evidence-gallery",
			".nxr-progress-track",
			".nxr-list-row",
		):
			self.assertIn(selector, css)

	def test_dashboard_context_is_consumed_by_related_pages(self) -> None:
		for relative_path in (
			"nexora/page/nexora_evidence/nexora_evidence.js",
			"nexora/page/nexora-reports/nexora-reports.js",
			"nexora/page/nexora_contracts/nexora_contracts.js",
			"nexora/page/nexora_purchase_requests/nexora_purchase_requests.js",
		):
			code = (APP_ROOT / relative_path).read_text(encoding="utf-8")
			self.assertIn("frappe.route_options", code)
			self.assertIn("launchOptions.project", code)

	def test_financial_report_sends_resolved_payload(self) -> None:
		code = (APP_ROOT / "nexora/page/nexora-reports/nexora-reports.js").read_text(encoding="utf-8")
		self.assertIn("args: { payload: payload() }", code)
		self.assertNotIn("args: { payload },", code)

	@staticmethod
	def _dashboard_code() -> str:
		path = APP_ROOT / "nexora/page/nexora-dashboard/nexora-dashboard.js"
		return path.read_text(encoding="utf-8")
