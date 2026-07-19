from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "erpnext" / "construcontrol" / "page_registry.py"
SPEC = importlib.util.spec_from_file_location("construcontrol_page_registry", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
	raise RuntimeError(f"Unable to load {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CanonicalPageRegistryTest(unittest.TestCase):
	def test_all_runtime_pages_have_one_filesystem_controller(self) -> None:
		definitions = MODULE.page_definitions()
		self.assertEqual(len(definitions), 8)
		self.assertEqual(MODULE.validate_page_contract(definitions), [])
		self.assertEqual(len({row["name"] for row in definitions}), 8)

	def test_database_page_values_never_embed_javascript(self) -> None:
		for definition in MODULE.page_definitions():
			with self.subTest(page=definition["name"]):
				values = MODULE.canonical_page_values(definition)
				self.assertEqual(values["script"], "")
				self.assertEqual(values["name"], values["page_name"])

	def test_legacy_page_writers_are_not_called(self) -> None:
		install = (ROOT / "erpnext" / "construcontrol" / "install.py").read_text(encoding="utf-8")
		self.assertEqual(install.count("ensure_canonical_pages"), 2)
		for obsolete in (
			"ensure_product_pages",
			"ensure_reporting_integration",
			"ensure_weekly_integration",
		):
			self.assertNotIn(obsolete, install)

		integration = (ROOT / "erpnext" / "construcontrol" / "integration.py").read_text(encoding="utf-8")
		self.assertNotIn("def _ensure_page", integration)
		self.assertNotIn('["pages"]', integration)

		for path in (
			ROOT / "erpnext" / "construcontrol" / "reporting_install.py",
			ROOT / "erpnext" / "construcontrol" / "weekly_install.py",
		):
			self.assertNotIn('"doctype": "Page"', path.read_text(encoding="utf-8"))

	def test_runtime_assets_contain_metadata_without_embedded_scripts(self) -> None:
		assets = json.loads(
			(ROOT / "erpnext" / "construcontrol" / "runtime" / "assets.json").read_text(encoding="utf-8")
		)
		self.assertEqual(len(assets["pages"]), 8)
		self.assertTrue(all(not row.get("script") for row in assets["pages"]))


if __name__ == "__main__":
	unittest.main()
