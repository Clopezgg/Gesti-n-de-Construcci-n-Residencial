from __future__ import annotations

import pathlib
import re
import unittest

PACKAGE = pathlib.Path(__file__).resolve().parents[1]
SHELL_JS = PACKAGE / "public/js/nexora_shell.js"
HOOKS_PY = PACKAGE / "hooks.py"


class TestClientRouteGuardContract(unittest.TestCase):
	"""Bloque 154 — capa de cliente de la guarda del Desk crudo.

	`nexora.shell_guard_core` (probado en `test_shell_guard_core.py`) es la única
	fuente de verdad para la lógica de la guarda del lado servidor; estas pruebas
	verifican que la capa de cliente en `nexora_shell.js` exista, esté conectada a
	`sync()` (el mismo punto que ya reacciona a cada cambio de ruta) y use la misma
	condición de exención — nunca System Manager ni NEXORA Administrator, siempre
	dejando pasar `nexora-*` y `nxr-*`.
	"""

	def source(self) -> str:
		return SHELL_JS.read_text(encoding="utf-8")

	def test_the_route_guard_function_exists(self) -> None:
		code = self.source()
		self.assertIn("function enforceRouteGuard() {", code)
		self.assertIn("function routeGuardApplies() {", code)
		self.assertIn("function isExemptRoute(route) {", code)

	def test_the_guard_uses_the_shared_exemption_helper(self) -> None:
		"""Bloque 155: `enforceRouteGuard()` debe decidir a través de
		`isExemptRoute()`, no repetir la comprobación inline — así la corrección
		del hallazgo real (`route[0]` es el tipo de vista, no el slug, para
		`Form`/`List`) vive en un solo lugar para las dos ramas (permitir y
		reafirmar)."""
		code = self.source()
		guard_block = code.split("function enforceRouteGuard() {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn("isExemptRoute(route)", guard_block)
		self.assertIn("isExemptRoute(still)", guard_block)

	def test_the_route_guard_runs_on_every_sync_before_mounting_the_shell(self) -> None:
		"""`sync()` ya corre en cada cambio de ruta (Bloque original de la carcasa) y en
		el arranque (`install()` llama a `schedule()` una vez). Conectar la guarda ahí,
		en vez de un segundo `frappe.router.on("change", ...)`, evita una segunda fuente
		de verdad sobre cuándo se ejecuta."""
		code = self.source()
		sync_block = code.split("function sync() {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn("if (enforceRouteGuard()) return;", sync_block)

	def test_both_administrator_tier_roles_are_exempt(self) -> None:
		code = self.source()
		self.assertIn('const RESTRICTED_ADMIN_ROLES = ["System Manager", "NEXORA Administrator"];', code)

	def test_all_five_nexora_roles_are_listed_as_scoped(self) -> None:
		code = self.source()
		self.assertIn("const NEXORA_SCOPED_ROLES = [", code)
		block = code.split("const NEXORA_SCOPED_ROLES = [", 1)[1].split("];", 1)[0]
		roles = set(re.findall(r'"([^"]+)"', block))
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

	def test_the_guard_redirects_to_the_dashboard_route_not_a_bare_path(self) -> None:
		"""La guarda de cliente usa `frappe.set_route`, no `window.location` — mismo
		mecanismo de navegación que el resto de la carcasa (`goToPaletteRoute`,
		`gotoRoute`), para no forzar una recarga completa de la SPA."""
		code = self.source()
		guard_block = code.split("function enforceRouteGuard() {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn('frappe.set_route("nexora-dashboard")', guard_block)

	def test_the_guard_allows_both_nexora_and_nxr_route_prefixes(self) -> None:
		"""Bloquear solo `nexora-*` habría roto los enlaces reales a `NXR Contract`/
		`NXR Operation`/etc. que varias pantallas ya construyen con
		`frappe.utils.get_form_link()` — mismo hallazgo que motiva la lista de
		prefijos permitidos en `nexora.shell_guard_core.ALLOWED_APP_PREFIXES`."""
		code = self.source()
		exempt_block = code.split("function isExemptRoute(route) {", 1)[1].split(
			"\n\t}", 1
		)[0]
		self.assertIn('route.startsWith("nexora-")', exempt_block)
		self.assertIn('route.startsWith("nxr-")', exempt_block)

	def test_the_guard_falls_back_to_the_url_path_not_just_the_route_array(
		self,
	) -> None:
		"""Hallazgo real del Bloque 155: `frappe.get_route()[0]` es `"Form"`/`"List"`
		para las vistas nativas de un DocType real (`NXR Operation` incluido) — el
		slug vive en `route[1]`, no en `route[0]`. Solo las páginas propias de
		NEXORA devuelven el slug directamente en `route[0]`. Sin este respaldo por
		ruta, un enlace real a `NXR Operation`/`NXR Contract` rebotaba al panel
		para cualquier rol sin administrador pese a que el servidor sí lo dejaba
		pasar — confirmado con evidencia real de CI (`__nxrRouteWatch`:
		`[null, "Form", "nexora-dashboard"]`)."""
		code = self.source()
		exempt_block = code.split("function isExemptRoute(route) {", 1)[1].split(
			"\n\t}", 1
		)[0]
		self.assertIn("window.location.pathname", exempt_block)
		self.assertIn('path.startsWith("/app/nexora-")', exempt_block)
		self.assertIn('path.startsWith("/app/nxr-")', exempt_block)


class TestServerRouteGuardIsWired(unittest.TestCase):
	def source(self) -> str:
		return HOOKS_PY.read_text(encoding="utf-8")

	def test_the_guard_is_registered_under_update_website_context(self) -> None:
		"""No en `before_request`: verificado contra el código real de Frappe que
		`frappe.Redirect` solo produce una redirección HTTP real dentro del
		renderizado de una página `www` (`update_website_context`), no en el
		manejador genérico de `before_request` — confirmado por un fallo real de
		CI con la primera versión de este bloque."""
		code = self.source()
		hook_block = code.split("update_website_context = [", 1)[1].split("]", 1)[0]
		self.assertIn('"nexora.shell_guard.enforce"', hook_block)

	def test_the_guard_is_not_registered_as_a_before_request_hook(self) -> None:
		code = self.source()
		before_request_block = code.split("before_request = [", 1)[1].split("]", 1)[0]
		self.assertNotIn("shell_guard", before_request_block)


if __name__ == "__main__":
	unittest.main()
