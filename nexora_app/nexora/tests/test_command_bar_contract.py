from __future__ import annotations

import pathlib
import re
import unittest

PACKAGE = pathlib.Path(__file__).resolve().parents[1]
SHELL_JS = PACKAGE / "public/js/nexora_shell.js"
SHELL_CSS = PACKAGE / "public/css/nexora_shell.css"


class TestCommandBarJsContract(unittest.TestCase):
	"""NXR-UX-0008 — paleta de comandos (Ctrl+K/Cmd+K).

	No existía ningún atajo de teclado global ni un catálogo de "qué necesita
	hacer" — la barra superior solo ofrecía "Buscar" y "Registrar ingreso" fijos.
	Estas pruebas verifican que la paleta nueva lea sus destinos de `SECTIONS`
	(la misma lista que ya pinta el cajón lateral) en el momento de abrir, en vez
	de mantener un segundo catálogo que pueda desalinearse.
	"""

	def source(self) -> str:
		return SHELL_JS.read_text(encoding="utf-8")

	def test_palette_items_reads_sections_live_not_a_copy(self) -> None:
		code = self.source()
		self.assertIn("function paletteItems() {", code)
		body = code.split("function paletteItems() {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn("SECTIONS.flatMap(", body)

	def test_global_shortcut_is_gated_to_ctrl_or_cmd_k(self) -> None:
		code = self.source()
		install = code.split("function install() {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn('event.key === "k" || event.key === "K"', install)
		self.assertIn("event.ctrlKey || event.metaKey", install)
		self.assertIn("event.preventDefault();", install)

	def test_shortcut_only_opens_on_nexora_routes(self) -> None:
		code = self.source()
		open_fn = code.split("function openPalette() {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn("if (!belongsToNexora()) return;", open_fn)

	def test_escape_and_enter_are_handled_without_a_second_navigation_path(self) -> None:
		"""Enter y las flechas deciden sobre las mismas filas que el clic ya navega
		con `goToPaletteRoute`/`frappe.set_route` — nunca una segunda función que
		construya su propia ruta."""
		code = self.source()
		keydown = code.split("function onPaletteKeydown(event, node) {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn('event.key === "Escape"', keydown)
		self.assertIn("goToPaletteRoute(", keydown)
		go_to_route = code.split("function goToPaletteRoute(route, report) {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn("frappe.set_route(route);", go_to_route)
		self.assertEqual(1, code.count("function goToPaletteRoute("))

	def test_filter_matches_against_the_same_translated_labels_sections_renders(self) -> None:
		code = self.source()
		render = code.split("function renderPaletteList(node, query) {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn("__(item.label).toLowerCase()", render)

	def test_palette_is_exposed_only_through_the_global_shortcut_not_a_visible_button(self) -> None:
		"""Alcance deliberadamente acotado: nunca un segundo disparador con un
		atributo propio solo para la paleta. RECONSTRUCCIÓN VISUAL DEFINITIVA
		agregó el buscador universal del topbar como entrada visible real, pero
		lo hizo reutilizando el mismo botón/atributo ya real (`data-shell-search`)
		en vez de inventar uno nuevo — sigue habiendo un único catálogo y un único
		disparador de teclado (Ctrl/Cmd+K), ahora con una segunda forma real de
		llegar a la misma paleta."""
		code = self.source()
		self.assertNotIn("data-shell-command", code)

	def test_palette_never_builds_its_own_route_catalog(self) -> None:
		routes_in_palette = re.findall(r'data-command-route="\$\{item\.route\}"', self.source())
		self.assertEqual(1, len(routes_in_palette))


class TestCommandBarCssContract(unittest.TestCase):
	def source(self) -> str:
		return SHELL_CSS.read_text(encoding="utf-8")

	def test_hidden_attribute_actually_hides_the_panel(self) -> None:
		code = self.source()
		self.assertIn(".nxr-command-bar[hidden] {\n\tdisplay: none;\n}", code)

	def test_selected_row_does_not_rely_on_color_alone(self) -> None:
		"""Mismo criterio de accesibilidad que el resto de la carcasa: la fila
		seleccionada se distingue por su propio estado ARIA, no solo por un
		matiz de color que alguien con bajo contraste podría no percibir."""
		code = self.source()
		self.assertIn('.nxr-command-bar__item[aria-selected="true"]', code)

	def test_panel_sits_above_the_drawer_scrim(self) -> None:
		code = self.source()
		block = code.split(".nxr-command-bar {", 1)[1].split("\n}", 1)[0]
		self.assertIn("calc(var(--nxr-z-nav) + 3)", block)
