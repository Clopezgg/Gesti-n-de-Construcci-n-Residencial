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
		self.assertIn("new MutationObserver(() => summarize(table, summary))", code)

	def test_the_export_survives_commas_quotes_and_accents(self) -> None:
		"""Un CSV que rompe con una coma en el concepto no sirve para trabajar."""
		code = self.source()
		self.assertIn('replace(/"/g, \'""\')', code, "las comillas deben escaparse")
		self.assertIn("﻿", code, "sin BOM Excel abre los acentos rotos")
		self.assertIn("text/csv;charset=utf-8", code)

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
