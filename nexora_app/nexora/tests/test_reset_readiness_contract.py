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


REPO_ROOT = APP_ROOT.parents[1]
RESET_SCRIPT = REPO_ROOT / "scripts/nexora_environment_reset.sh"


class TestEnvironmentResetScriptNeverBypassesTheRealSafetyGuard(unittest.TestCase):
	"""ORDEN FINAL DE CIERRE TOTAL, Objetivo 1: el script orquestador real del
	reset (Sección A/B del runbook) debe exigir confirmación explícita, hacer
	respaldo real antes de tocar nada, y nunca inventar una bandera de
	"forzar" que evite `before_uninstall()` — ese guard rechaza
	incondicionalmente cuando ya hay `NXR Operation` reales (Bloque 159), por
	diseño, y este script no puede tener la última palabra sobre esa
	decisión."""

	def source(self) -> str:
		return RESET_SCRIPT.read_text(encoding="utf-8")

	def test_the_script_exists_and_is_executable(self) -> None:
		self.assertTrue(RESET_SCRIPT.is_file())
		import os
		import stat

		mode = os.stat(RESET_SCRIPT).st_mode
		self.assertTrue(mode & stat.S_IXUSR, "el script debe ser ejecutable")

	def test_it_requires_explicit_confirmation_before_touching_anything(self) -> None:
		source = self.source()
		self.assertIn("--confirm", source)
		self.assertIn('CONFIRMED" -ne 1', source)

	def test_it_backs_up_before_uninstalling_and_counts_before_and_after(self) -> None:
		source = self.source()
		backup_at = source.index("bench --site \"$SITE\" backup --with-files")
		uninstall_at = source.index("bench --site \"$SITE\" uninstall-app nexora")
		self.assertLess(backup_at, uninstall_at, "el respaldo debe ocurrir antes de desinstalar")
		self.assertIn("count_business_records", source)
		precount_run_at = source.index("count_business_records", 0, backup_at)
		postcount_run_at = source.rindex("count_business_records")
		self.assertLess(precount_run_at, uninstall_at, "el conteo previo debe ejecutarse antes de desinstalar")
		self.assertGreater(
			postcount_run_at, uninstall_at, "el conteo posterior debe ejecutarse después de reinstalar"
		)

	def test_it_never_introduces_a_force_flag_around_before_uninstall(self) -> None:
		"""No puede inventar una manera de saltarse la guarda real — solo
		puede documentar que existe y por qué se respeta."""
		source = self.source().lower()
		for forbidden in ("--force", "force-uninstall", "ignore_permissions", "bypass"):
			self.assertNotIn(forbidden, source)
		self.assertIn("before_uninstall", self.source())


if __name__ == "__main__":
	unittest.main()
