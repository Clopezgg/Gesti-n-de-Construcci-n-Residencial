from __future__ import annotations

import json
import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestDashboardContract(unittest.TestCase):
	@staticmethod
	def _dashboard_code() -> str:
		return (APP_ROOT / "nexora/page/nexora_dashboard/nexora_dashboard.js").read_text(encoding="utf-8")

	def test_dashboard_module_and_service_exist(self) -> None:
		self.assertTrue((APP_ROOT / "dashboard/__init__.py").is_file())
		self.assertTrue((APP_ROOT / "dashboard/service.py").is_file())

	def test_dashboard_and_search_pages_exist(self) -> None:
		for page_name in ("nexora-dashboard", "nexora-search"):
			# Frappe resolves page assets with frappe.scrub(name), so the folder and the
			# asset filenames use underscores even when the Page record uses hyphens.
			folder = page_name.replace("-", "_")
			root = APP_ROOT / f"nexora/page/{folder}"
			payload = json.loads((root / f"{folder}.json").read_text(encoding="utf-8"))
			self.assertEqual(page_name, payload["page_name"])
			self.assertIn("frappe.pages", (root / f"{folder}.js").read_text(encoding="utf-8"))

	def test_dashboard_keeps_project_control_reference(self) -> None:
		code = self._dashboard_code()
		self.assertIn("const projectControl = page.add_field", code)
		self.assertIn("projectControl.get_value()", code)
		self.assertNotIn("controls.project.get_value()", code)

	def test_dashboard_exposes_direct_income_and_expense_actions(self) -> None:
		code = self._dashboard_code()
		for marker in (
			'data-action="income"',
			'data-action="expense"',
			"frappe.route_options",
			"nexora_action: action",
			"project: projectControl.get_value()",
		):
			self.assertIn(marker, code)

	def test_dashboard_uses_official_product_identity(self) -> None:
		code = self._dashboard_code()
		self.assertIn('title: __("NEXORA")', code)
		self.assertIn("Gestión Integral de Fondos, Proyectos y Operaciones", code)
		self.assertNotIn("NEXORA — Control de obras", code)

	def test_dashboard_translates_technical_operation_values(self) -> None:
		code = self._dashboard_code()
		for marker in (
			'Inflow: __("Ingreso")',
			'Outflow: __("Gasto")',
			'"Internal Transfer": __("Transferencia interna")',
			'"Real Return": __("Devolución real")',
			'Draft: __("Borrador")',
			'Executed: __("Registrado definitivamente")',
			'Posted: __("Registrado definitivamente")',
			'"Compensated Total": __("Corregido totalmente")',
		):
			self.assertIn(marker, code)

	def test_dashboard_handles_loading_failures_with_actionable_copy(self) -> None:
		code = self._dashboard_code()
		for marker in (
			"try {",
			"catch (error)",
			'title: __("Resumen no disponible")',
			"Revise la conexión, el proyecto o sus permisos y vuelva a intentar.",
			'attr({ "data-state": "error", "aria-busy": "false" })',
		):
			self.assertIn(marker, code)

	def test_dashboard_snapshot_uses_native_deadline_instead_of_frappe_thenable(self) -> None:
		code = self._dashboard_code()
		snapshot_request = code[
			code.index("function requestExecutiveSnapshot") : code.index("function renderIdentity")
		]
		load = code[code.index("async function load") : code.index("function render(data)")]
		for marker in (
			"return new Promise((resolve, reject) => {",
			"window.setTimeout(",
			"120000",
			"callback: (response) => finish(resolve, response?.message || {})",
			"error: (error) =>",
			"El resumen ejecutivo excedió 120 segundos.",
		):
			self.assertIn(marker, snapshot_request)
		self.assertIn(
			"const snapshot = await requestExecutiveSnapshot(snapshotPayload(), Boolean(freeze));",
			load,
		)
		self.assertNotIn("await frappe.call", load)
		self.assertIn("render(snapshot)", load)

	def test_dashboard_integrates_complete_operational_summary(self) -> None:
		code = self._dashboard_code()
		for marker in (
			"finance.total_available_hnl",
			"finance.total_reserved_hnl",
			"executive.spent_hnl",
			"budgets.total_available_hnl",
			"pending_accounts",
			"progress.physical_percent",
			"nxr-evidence-gallery",
			"nxr-alert-rows",
			"nxr-contract-rows",
		):
			self.assertIn(marker, code)

	def test_dashboard_service_reconciles_against_canonical_effect_ledger(self) -> None:
		code = (APP_ROOT / "dashboard/service.py").read_text(encoding="utf-8")
		for marker in (
			"source_states",
			'"NXR Operation Effect"',
			'"Reserved"',
			'"Budget"',
			'{"Commitment Reserve", "Commitment Release"}',
			'"NXR Contract Estimate"',
			'"NXR Progress Record"',
			'"NXR Evidence"',
		):
			self.assertIn(marker, code)

	def test_service_has_whitelisted_permission_checked_functions(self) -> None:
		code = (APP_ROOT / "dashboard/service.py").read_text(encoding="utf-8")
		for marker in (
			"@frappe.whitelist",
			"def universal_search",
			"def get_dashboard_summary",
			"require_action",
		):
			self.assertIn(marker, code)

	def test_workspace_has_dashboard_and_search_shortcuts(self) -> None:
		payload = json.loads((APP_ROOT / "nexora/workspace/nexora/nexora.json").read_text(encoding="utf-8"))
		shortcuts = [shortcut["label"] for shortcut in payload.get("shortcuts", [])]
		self.assertIn("Panel principal", shortcuts)
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

	def test_dashboard_is_the_canonical_desk_home(self) -> None:
		hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
		install = (APP_ROOT / "install.py").read_text(encoding="utf-8")
		self.assertIn('"route": "/app/nexora-dashboard"', hooks)
		self.assertIn('NEXORA_HOME_PAGE = "nexora-dashboard"', install)
		self.assertIn('frappe.db.set_default("desktop:home_page", NEXORA_HOME_PAGE)', install)

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
			"nexora/page/nexora_reports/nexora_reports.js",
			"nexora/page/nexora_contracts/nexora_contracts.js",
			"nexora/page/nexora_purchase_requests/nexora_purchase_requests.js",
		):
			code = (APP_ROOT / relative_path).read_text(encoding="utf-8")
			self.assertIn("frappe.route_options", code)
			self.assertIn("launchOptions.project", code)

	def test_financial_report_sends_resolved_payload(self) -> None:
		code = (APP_ROOT / "nexora/page/nexora_reports/nexora_reports.js").read_text(encoding="utf-8")
		self.assertIn("args: { payload: payload() }", code)
		self.assertNotIn("args: { payload },", code)


if __name__ == "__main__":
	unittest.main()
