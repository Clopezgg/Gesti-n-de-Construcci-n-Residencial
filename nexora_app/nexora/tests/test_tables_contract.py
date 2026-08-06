from __future__ import annotations

import pathlib
import re
import unittest

APP_ROOT = pathlib.Path(__file__).resolve().parents[1]
TABLES = APP_ROOT / "public/js/nexora_tables.js"
HOOKS = APP_ROOT / "hooks.py"
PAGES = APP_ROOT / "nexora/page"


class TestTablesContract(unittest.TestCase):
	"""Capítulo 33: «Las tablas deberán permitir trabajar. No únicamente consultar.»

	Dieciséis tablas repartidas en diez pantallas y ninguna se podía ordenar; solo
	Reportes exportaba. El Capítulo 34 impide resolverlo pantalla por pantalla: sería
	crear diez variantes del mismo comportamiento.
	"""

	def source(self) -> str:
		return TABLES.read_text(encoding="utf-8")

	def test_the_shared_module_exists_and_loads_before_the_screens(self) -> None:
		self.assertTrue(TABLES.is_file(), "falta el módulo compartido de tablas")
		hooks = HOOKS.read_text(encoding="utf-8")
		self.assertIn(
			'"/assets/nexora/js/nexora_tables.js"',
			hooks,
			"el módulo debe cargarse en toda la aplicación, no por pantalla",
		)
		includes = hooks.split("app_include_js = [", 1)[1].split("]", 1)[0]
		bundles = re.findall(r'"/assets/nexora/js/([a-z_]+\.js)"', includes)
		self.assertIn("nexora_tables.js", bundles)

	def test_every_table_gains_the_capabilities_the_chapter_demands(self) -> None:
		code = self.source()
		for capability, marker in (
			("ordenar", "aria-sort"),
			("exportar", "nxr-table-export"),
			("resumen", "nxr-table-summary"),
		):
			with self.subTest(capability=capability):
				self.assertIn(marker, code)
		# Ordenar con el teclado, no solo con el ratón: la tabla también se opera en móvil
		# y con lector de pantalla (Capítulo 37).
		self.assertIn('cell.addEventListener("keydown"', code)
		self.assertIn("cell.tabIndex = 0", code)
		# El resumen sigue al repintado de la pantalla en vez de quedarse congelado.
		self.assertIn("const observer = new MutationObserver(refresh);", code)
		self.assertIn("observer.observe(table.tBodies[0]", code)
		self.assertIn("summarize(table, summary);", code.split("const refresh = () => {", 1)[1])

	def test_the_export_survives_commas_quotes_and_accents(self) -> None:
		"""Un CSV que rompe con una coma en el concepto no sirve para trabajar."""
		code = self.source()
		self.assertIn('replace(/"/g, \'""\')', code, "las comillas deben escaparse")
		self.assertIn("\\uFEFF", code, "sin BOM Excel abre los acentos rotos")
		self.assertIn("text/csv;charset=utf-8", code)

	def test_the_toolbar_follows_the_table_it_belongs_to(self) -> None:
		"""En móvil la pantalla sustituye la tabla por tarjetas y la oculta (Capítulo 37).
		Una barra con «Exportar CSV» y un recuento flotando sobre una tabla que el usuario
		no ve promete sobre algo que no está delante."""
		code = self.source()
		self.assertIn("function syncToolbar(table, bar)", code)
		body = code.split("function syncToolbar(table, bar) {", 1)[1].split("\n\t}", 1)[0]
		# `offsetParent` también vale nulo cuando un ancestro está posicionado de forma
		# fija, así que confunde «no se ve» con «se ve y cuelga de algo fijo». El recorrido
		# real lo mostró en escritorio: tabla visible y botón «Exportar CSV» oculto durante
		# sesenta segundos. Los rectángulos del elemento valen cero solo si no se pinta.
		self.assertIn(
			"table.getClientRects().length === 0",
			body,
			"la barra sigue a la tabla realmente pintada",
		)
		self.assertNotIn("table.offsetParent", body)
		self.assertIn("bar.hidden = hidden", body)
		# Definirla no basta: hay que llamarla en cada refresco, que es donde se decide.
		refresh = code.split("const refresh = () => {", 1)[1].split("};", 1)[0]
		self.assertIn("syncToolbar(table, bar);", refresh)
		# Girar el teléfono cambia la representación sin tocar el DOM: el observador de
		# mutaciones no basta.
		self.assertIn('window.addEventListener(\n\t\t"resize",', code)
		self.assertIn("for (const entry of active.values()) entry.refresh();", code)

	def test_a_table_that_becomes_visible_recovers_its_toolbar(self) -> None:
		"""Una tabla mejorada mientras su pantalla aún no se pintaba nacía con la barra
		oculta —correctamente, en ese instante nadie la veía— y nada volvía a revisarlo: el
		observador del cuerpo solo mira los datos, y mostrar una pantalla no cambia el
		tamaño de la ventana. El recorrido real encontró la tabla visible en escritorio y
		el botón «Exportar CSV» oculto en las ciento veinticuatro comprobaciones."""
		code = self.source()
		enhance_all = code.split("function enhanceAll() {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn(
			"for (const entry of active.values()) entry.refresh();",
			enhance_all,
			"cada pasada vuelve a decidir la visibilidad de las barras ya instaladas",
		)
		# Frappe muestra y esconde pantallas cambiando atributos, no nodos: un observador
		# que solo mira `childList` no despierta cuando la tabla pasa a verse.
		install = code.split("function install() {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn("attributes: true", install)
		self.assertIn('attributeFilter: ["class", "style", "hidden"]', install)

	def test_the_toolbar_only_reaches_tables_that_are_work_surfaces(self) -> None:
		"""El Capítulo 34 pide un único componente reutilizable, no que toda `<table>` se
		convierta en una rejilla de datos. El resumen de la línea del movimiento tiene una
		sola fila: ordenarla no significa nada y la barra empujó el botón «Continuar» del
		asistente debajo de la barra fija de la aplicación, rompiendo un flujo que
		funcionaba."""
		code = self.source()
		self.assertIn("function isWorkSurface(table)", code)
		guard = code.split("function isWorkSurface(table) {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn('table.dataset.nxrTable === "plain"', guard)
		self.assertIn("bodyRows(table).length > 1", guard)
		# Definir la guarda no basta: `enhance` tiene que abandonar antes de marcar la
		# tabla y de insertar la barra, o la excepción no existe.
		enhance = code.split("function enhance(table) {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn("if (!isWorkSurface(table)) return;", enhance)
		early, marked = enhance.split('table.dataset[ENHANCED] = "1";', 1)
		self.assertIn("isWorkSurface", early, "la guarda decide antes de marcar la tabla")
		self.assertNotIn("insertBefore(bar", early)
		self.assertIn("insertBefore(bar", marked)

		entry = (PAGES / "nexora_operations/nexora_operations.js").read_text(encoding="utf-8")
		self.assertIn(
			'class="table nxr-entry-table" data-nxr-table="plain"',
			entry,
			"la línea del movimiento se declara tabla plana: no es superficie de trabajo",
		)

	def test_a_table_that_leaves_the_document_takes_its_observers_with_it(self) -> None:
		"""Las pantallas repintan con `innerHTML`: la tabla mejorada se sustituye entera y
		varias veces por sesión. Un observador por tabla y un listener de `resize` por
		tabla retenían nodos que ya no están en el documento."""
		code = self.source()
		self.assertIn("const active = new Map();", code)
		self.assertIn(
			"active.set(table, { refresh, observer, bar, head, body: table.tBodies[0] });",
			code,
		)
		release = code.split("function release() {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn("table.isConnected &&", release)
		drop = code.split("function drop(table, entry) {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn("entry.observer.disconnect();", drop)
		self.assertIn("active.delete(table);", drop)

	def test_a_table_whose_body_is_replaced_is_enhanced_again(self) -> None:
		"""El panel repinta `thead` y `tbody` conservando la misma `<table>`. La tabla
		seguía marcada como mejorada, así que nadie la volvía a tocar: el observador
		miraba un cuerpo ya desconectado y las cabeceras nuevas nacían sin manejador de
		orden. La tabla perdía la ordenación y el recuento sin que nada lo dijera."""
		code = self.source()
		release = code.split("function release() {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn("entry.body === table.tBodies[0]", release)
		self.assertIn("entry.head === table.tHead?.rows?.[0]", release)
		self.assertIn("drop(table, entry);", release)
		# Soltarla no basta: hay que desmarcarla y retirar su barra, o `enhance` no
		# volvería a entrar y la siguiente pasada dejaría dos barras.
		drop = code.split("function drop(table, entry) {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn("delete table.dataset[ENHANCED];", drop)
		self.assertIn("entry.bar.remove();", drop)
		# Definirlo no basta: se suelta en cada pasada y al cambiar el tamaño.
		self.assertIn("release();", code.split("function enhanceAll() {", 1)[1].split("\n\t}", 1)[0])
		self.assertEqual(
			1,
			code.count('window.addEventListener("resize"') + code.count('\t\t"resize",'),
			"un único listener global de resize, no uno por tabla",
		)

	def test_no_screen_reimplements_sorting_on_its_own(self) -> None:
		"""Capítulo 34: un único componente, nunca varias variantes del mismo
		comportamiento."""
		offenders: list[str] = []
		for page in sorted(PAGES.glob("*/[a-z]*.js")):
			source = page.read_text(encoding="utf-8")
			if "aria-sort" in source or "nxr-sortable" in source:
				offenders.append(page.name)
		self.assertEqual([], offenders, "el orden vive en nexora_tables.js")


if __name__ == "__main__":
	unittest.main()
