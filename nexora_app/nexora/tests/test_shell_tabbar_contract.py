from __future__ import annotations

import pathlib
import unittest

PACKAGE = pathlib.Path(__file__).resolve().parents[1]
SHELL_JS = PACKAGE / "public/js/nexora_shell.js"
SHELL_CSS = PACKAGE / "public/css/nexora_shell.css"


class TestShellTabbarJsContract(unittest.TestCase):
	"""NXR-UX-0014 — navegación móvil inferior.

	No existía ninguna barra inferior; el teléfono usaba el mismo cajón lateral que el
	escritorio, colapsado detrás de una hamburguesa. Estas pruebas verifican que la
	barra nueva reutilice `SECTIONS`/los mismos iconos/el mismo manejador de clic y de
	estado activo — no una segunda fuente de rutas ni una segunda lógica de navegación.
	"""

	def source(self) -> str:
		return SHELL_JS.read_text(encoding="utf-8")

	def test_tabbar_has_four_frequent_destinations_plus_more(self) -> None:
		code = self.source()
		self.assertIn("const TABBAR_ITEMS = [", code)
		block = code.split("const TABBAR_ITEMS = [", 1)[1].split("\n\t];", 1)[0]
		self.assertEqual(4, block.count('{ route: "'), "cuatro destinos frecuentes, no más")
		# Los cuatro deben ser rutas reales de SECTIONS, no inventadas.
		for route in ("nexora-dashboard", "nexora-operations", "nexora-finance", "nexora-search"):
			self.assertIn(f'route: "{route}"', block)

	def test_tabbar_items_are_a_subset_of_the_real_sections_not_new_routes(self) -> None:
		code = self.source()
		sections_block = code.split("const SECTIONS = [", 1)[1].split("\n\t];", 1)[0]
		tabbar_block = code.split("const TABBAR_ITEMS = [", 1)[1].split("\n\t];", 1)[0]
		import re

		tabbar_routes = set(re.findall(r'route: "([^"]+)"', tabbar_block))
		section_routes = set(re.findall(r'route: "([^"]+)"', sections_block))
		self.assertTrue(tabbar_routes.issubset(section_routes), "la barra inferior no debe inventar rutas")

	def test_more_button_opens_the_same_drawer_as_the_desktop_hamburger(self) -> None:
		code = self.source()
		self.assertIn("data-shell-tab-more", code)
		self.assertIn(
			'node.querySelector("[data-shell-tab-more]").addEventListener("click", () => openDrawer(true));',
			code,
		)

	def test_open_drawer_keeps_both_triggers_in_sync(self) -> None:
		code = self.source()
		drawer = code.split("function openDrawer(open) {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn('shell.querySelectorAll("[data-shell-drawer], [data-shell-tab-more]")', drawer)
		self.assertIn('trigger.setAttribute("aria-expanded"', drawer)

	def test_tab_links_reuse_the_generic_route_click_handler(self) -> None:
		"""Los enlaces de la barra inferior llevan el mismo atributo `data-shell-route`
		que el cajón lateral: el manejador de clic y `paintActive()` ya son genéricos
		sobre ese atributo, así que no hacía falta un segundo manejador ni una segunda
		función de estado activo."""
		code = self.source()
		self.assertIn(
			'class="nxr-shell__tab" href="/app/${item.route}" data-shell-route="${item.route}"', code
		)
		paint = code.split("function paintActive() {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn('shell.querySelectorAll("[data-shell-route]")', paint)

	def test_tabbar_is_exposed_for_reuse(self) -> None:
		code = self.source()
		self.assertIn("tabbarItems: TABBAR_ITEMS", code)


class TestShellTabbarCssContract(unittest.TestCase):
	def source(self) -> str:
		return SHELL_CSS.read_text(encoding="utf-8")

	def test_tabbar_hidden_by_default_only_shown_on_phone(self) -> None:
		code = self.source()
		self.assertIn(".nxr-shell__tabbar {\n\tdisplay: none;\n}", code)
		self.assertIn("@media (max-width: 640px)", code)

	def test_tabbar_respects_safe_area_and_reserves_body_space(self) -> None:
		"""Sin el relleno inferior de <body>, la barra fija tapa los últimos píxeles de
		cualquier página larga (mismo defecto de fondo que el shell ya evitó para la
		barra superior)."""
		code = self.source()
		self.assertIn("env(safe-area-inset-bottom, 0px)", code)
		self.assertIn("padding-bottom: calc(56px + env(safe-area-inset-bottom, 0px));", code)

	def test_tab_touch_target_meets_the_minimum(self) -> None:
		code = self.source()
		tab_block = code.split(".nxr-shell__tab {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn("min-height: 56px", tab_block)
		self.assertIn("touch-action: manipulation", tab_block)

	def test_active_state_does_not_rely_on_color_alone(self) -> None:
		"""Mismo criterio de accesibilidad que el cajón lateral: color más otro rasgo
		(aquí, el ícono se vuelve opaco), no solo el color, para quien no percibe bien
		el contraste."""
		code = self.source()
		self.assertIn('.nxr-shell__tab[aria-current="page"]', code)
		active_block = code.split('.nxr-shell__tab[aria-current="page"] svg,', 1)[1].split("\n\t}", 1)[0]
		self.assertIn("opacity: 1", active_block)

	def test_top_bar_search_and_hamburger_are_not_duplicated_once_the_tabbar_exists(self) -> None:
		"""La barra inferior asume búsqueda y acceso al cajón; conservar el resto del
		clúster (buscador universal, cajón, ayuda/notificaciones/tema, usuario) arriba
		habría sido la misma acción varias veces a la vista en el ancho más angosto."""
		code = self.source()
		phone_block = code.split("@media (max-width: 640px) {", 2)[1]
		self.assertIn(
			".nxr-shell__universal-search,\n\t.nxr-shell__drawer,\n\t.nxr-shell__topbar-icon,\n\t"
			".nxr-shell__user {\n\t\tdisplay: none;\n\t}",
			phone_block,
		)
