"""Cierre de producción, Paso 5: el runbook de reset exige una identificación
exacta de qué DocType es un registro histórico de negocio — este contrato
verifica que la clasificación de `financial/reset_readiness.py` cubre
exactamente los DocTypes reales que hay hoy en el repositorio, ni de más ni
de menos, y que ninguna categoría se solapa con otra. Ejecuta AST/JSON real
sobre el árbol de DocTypes, no una lista copiada a mano dos veces.
"""

from __future__ import annotations

import json
import pathlib
import re
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent
DOCTYPE_ROOT = APP_ROOT / "nexora/doctype"
MODULE = APP_ROOT / "financial/reset_readiness.py"


def real_standalone_nxr_doctypes() -> set[str]:
	names = set()
	for folder in DOCTYPE_ROOT.iterdir():
		json_path = folder / f"{folder.name}.json"
		if not json_path.is_file():
			continue
		payload = json.loads(json_path.read_text(encoding="utf-8"))
		name = payload.get("name", "")
		if name.startswith("NXR") and not payload.get("istable"):
			names.add(name)
	return names


def classified_doctypes() -> list[str]:
	source = MODULE.read_text(encoding="utf-8")
	return re.findall(r'"(NXR [^"]+)"', source)


class TestResetReadinessClassificationIsComplete(unittest.TestCase):
	def test_every_real_standalone_doctype_is_classified_exactly_once(self) -> None:
		real = real_standalone_nxr_doctypes()
		classified = classified_doctypes()
		classified_set = set(classified)
		with self.subTest("no duplicates across categories"):
			duplicates = {name for name in classified_set if classified.count(name) > 1}
			self.assertEqual(set(), duplicates)
		with self.subTest("nothing classified that doesn't exist or is a child table"):
			self.assertEqual(set(), classified_set - real)
		with self.subTest("nothing real left unclassified"):
			self.assertEqual(set(), real - classified_set)

	def test_configuration_and_technical_catalogs_are_never_treated_as_business_data(self) -> None:
		source = MODULE.read_text(encoding="utf-8")
		config_block = source.split("CONFIGURATION_DOCTYPES_NEVER_PURGED = (", 1)[1].split(")", 1)[0]
		catalog_block = source.split("TECHNICAL_CATALOG_DOCTYPES = (", 1)[1].split(")", 1)[0]
		transactional_block = source.split("TRANSACTIONAL_BUSINESS_DOCTYPES = (", 1)[1].split(")", 1)[0]
		for name in re.findall(r'"(NXR [^"]+)"', config_block + catalog_block):
			with self.subTest(doctype=name):
				self.assertNotIn(f'"{name}"', transactional_block)

	def test_the_module_never_writes_only_counts(self) -> None:
		source = MODULE.read_text(encoding="utf-8")
		for forbidden in (
			"delete_doc",
			".insert(",
			".save(",
			".db_set(",
			"frappe.db.delete",
			"frappe.db.set_value",
		):
			self.assertNotIn(forbidden, source)

	def test_count_business_records_reports_every_category(self) -> None:
		source = MODULE.read_text(encoding="utf-8")
		body = source.split("def count_business_records()", 1)[1]
		for key in (
			"transactional_business_records",
			"master_data_requires_decision",
			"audit_and_system_logs",
			"configuration_never_purged",
			"technical_catalogs_never_purged",
			"users_total",
		):
			with self.subTest(key=key):
				self.assertIn(f'"{key}"', body)


if __name__ == "__main__":
	unittest.main()
