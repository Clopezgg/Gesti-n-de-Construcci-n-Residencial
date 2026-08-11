from __future__ import annotations

import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent
PROJECT_JS = APP_ROOT / "nexora/page/nexora_project/nexora_project.js"
PROJECT_CSS = APP_ROOT / "public/css/nexora_project.css"
DASHBOARD_JS = APP_ROOT / "nexora/page/nexora_dashboard/nexora_dashboard.js"


class TestProjectPageContract(unittest.TestCase):
	"""NXR-UX-0010/NXR-UX-0011: la pantalla de contexto 360° + timeline."""

	def source(self) -> str:
		return PROJECT_JS.read_text(encoding="utf-8")

	def test_page_files_exist(self) -> None:
		for relative in (
			"nexora/page/nexora_project/__init__.py",
			"nexora/page/nexora_project/nexora_project.json",
			"nexora/page/nexora_project/nexora_project.js",
		):
			self.assertTrue((APP_ROOT / relative).is_file(), relative)

	def test_page_is_reachable_by_the_same_nexora_roles_as_other_screens(self) -> None:
		import json

		payload = json.loads((APP_ROOT / "nexora/page/nexora_project/nexora_project.json").read_text())
		roles = {entry["role"] for entry in payload["roles"]}
		self.assertEqual(
			{
				"NEXORA Administrator",
				"NEXORA Finance Manager",
				"NEXORA Finance Operator",
				"NEXORA Auditor",
				"NEXORA Project Viewer",
			},
			roles,
		)

	def test_calls_the_two_new_backend_functions_not_a_third_reimplementation(self) -> None:
		code = self.source()
		self.assertIn("nexora.context360.service.get_project_overview", code)
		self.assertIn("nexora.context360.timeline.get_project_timeline", code)

	def test_uses_the_shared_ui_helpers_not_ad_hoc_formatting(self) -> None:
		code = self.source()
		for helper in ("window.nexora.ui.formatMoney", "window.nexora.ui.formatDate", "window.nexora.ui.escapeHtml",
			"window.nexora.ui.showError"):
			self.assertIn(helper, code)

	def test_reuses_the_money_row_component_from_bloque_16(self) -> None:
		code = self.source()
		self.assertIn("nxr-ds-money-row", code)
		self.assertIn('"reference"', code)
		self.assertIn('"pending"', code)
		self.assertIn('"spent"', code)
		self.assertIn('"available"', code)

	def test_inherits_project_from_route_options_or_active_context_like_other_pages(self) -> None:
		"""Mismo patrón ya usado por nexora_contracts.js — no una segunda forma de
		heredar el proyecto activo."""
		code = self.source()
		self.assertIn("frappe.route_options", code)
		self.assertIn("window.nexora.context?.activeProject?.()", code)
		self.assertIn("window.nexora.context?.onContextChange?.(", code)

	def test_drill_down_links_use_the_established_form_link_pattern(self) -> None:
		"""Mismo patrón que ya usa nexora_dashboard.js (`renderFunds`/`renderPayables`):
		no se inventa una segunda forma de enlazar al documento origen."""
		code = self.source()
		self.assertIn("frappe.utils.get_form_link(", code)

	def test_timeline_exception_is_marked_in_the_dom_for_styling(self) -> None:
		code = self.source()
		self.assertIn('data-exception="${event.is_exception}"', code)

	def test_empty_loading_and_error_states_are_all_handled(self) -> None:
		code = self.source()
		self.assertIn('data-state="empty"', code)
		self.assertIn('shell.attr("data-state", "loading")', code)
		self.assertIn('shell.attr("data-state", "error")', code)
		self.assertIn('shell.attr("data-state", "ready")', code)
		self.assertIn("Sin eventos todavía para este filtro", code)


class TestProjectPageCssContract(unittest.TestCase):
	def source(self) -> str:
		return PROJECT_CSS.read_text(encoding="utf-8")

	def test_never_touches_a_bare_element(self) -> None:
		code = self.source()
		for bare in ("\ndiv {", "\nspan {", "\np {", "\na {", "\nbutton {"):
			self.assertNotIn(bare, code)

	def test_grid_is_responsive_without_a_dedicated_media_query(self) -> None:
		code = self.source()
		self.assertIn("auto-fit", code)
		self.assertIn("minmax(", code)

	def test_phone_breakpoint_matches_the_shell_tabbar_breakpoint(self) -> None:
		"""Consistencia con NXR-UX-0014: el mismo punto de corte de teléfono
		(`nexora_shell.css`), no un número arbitrario distinto."""
		code = self.source()
		self.assertIn("@media (max-width: 640px)", code)

	def test_reduced_motion_is_respected(self) -> None:
		code = self.source()
		self.assertIn("@media (prefers-reduced-motion: reduce)", code)

	def test_exception_events_are_distinguished_by_shape_not_only_color(self) -> None:
		code = self.source()
		block = code.split('[data-exception="true"]', 1)[1].split("}", 1)[0]
		self.assertIn("border-radius", block)
		self.assertIn("var(--nxr-warning)", block)


class TestDashboardOpensProjectContext(unittest.TestCase):
	def test_dashboard_has_a_contextual_link_to_the_project_360_view(self) -> None:
		"""No es un destino nuevo en la navegación principal: solo alcanzable desde
		donde el proyecto activo ya está seleccionado."""
		code = DASHBOARD_JS.read_text(encoding="utf-8")
		self.assertIn("data-project-360", code)
		self.assertIn('frappe.set_route("nexora-project")', code)

	def test_the_link_does_not_fall_into_the_generic_finance_action_handler(self) -> None:
		code = DASHBOARD_JS.read_text(encoding="utf-8")
		# El botón nuevo usa un atributo distinto de `data-action`, que ya enruta
		# siempre a "nexora-finance" — de lo contrario el clic iría al lugar
		# equivocado sin ningún error visible.
		self.assertNotIn('data-action="open-project"', code)
		self.assertIn("data-project-360", code)
