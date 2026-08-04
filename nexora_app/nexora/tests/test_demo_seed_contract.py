from __future__ import annotations

import pathlib
import re
import unittest

APP_ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKAGE = APP_ROOT / "nexora"
SEEDS = PACKAGE / "financial/seeds.py"
OPERATIONS = PACKAGE / "nexora/page/nexora_operations/nexora_operations.js"
SMOKE = APP_ROOT.parent / "scripts/nexora_browser_smoke.mjs"


class TestDemoSeedContract(unittest.TestCase):
	"""El sitio demostrativo debe poder ejecutar los flujos que la pantalla exige.

	Un dato obligatorio sin ninguna opción sembrada no es un fallo de pruebas:
	es un usuario bloqueado frente a un campo vacío que no puede llenar.
	"""

	def test_expense_requires_a_beneficiary_entity(self) -> None:
		"""Deja explícito de dónde nace la obligación que el seed debe cubrir."""
		operations = OPERATIONS.read_text(encoding="utf-8")
		self.assertIn('required("beneficiary"', operations)
		beneficiary = operations.split('fieldname: "beneficiary"', 1)[1].split("},", 1)[0]
		self.assertIn('options: "NXR Entity"', beneficiary)

	def test_demo_seed_creates_the_beneficiary_the_expense_flow_demands(self) -> None:
		seeds = SEEDS.read_text(encoding="utf-8")
		self.assertIn("def _ensure_demo_entity()", seeds)
		self.assertIn("beneficiary = _ensure_demo_entity()", seeds)
		helper = seeds.split("def _ensure_demo_entity()", 1)[1].split("\ndef ", 1)[0]
		self.assertIn("create_entity", helper)
		self.assertIn("DEMO_ENTITY_KEY", helper, "la entidad demostrativa debe ser idempotente")
		self.assertIn('"Active"', helper, "un proveedor en borrador no representa la operación real")
		self.assertIn('"beneficiary": beneficiary,', seeds, "el resultado debe exponer la entidad creada")

	def test_the_demo_entity_can_actually_be_activated(self) -> None:
		"""`NXR Entity.validate` rechaza activar una entidad sin identificador,
		contacto ni usuario vinculado. Sembrarla sin contacto rompe la instalación
		entera en el paso de datos demostrativos, no solo el directorio."""
		controller = (PACKAGE / "nexora/doctype/nxr_entity/nxr_entity.py").read_text(encoding="utf-8")
		self.assertIn(
			'if self.status == "Active" and not (self.identifiers or self.contacts or self.linked_user)',
			controller,
			"si la regla de activación cambia, este contrato debe revisarse con ella",
		)
		helper = SEEDS.read_text(encoding="utf-8").split("def _ensure_demo_entity()", 1)[1]
		helper = helper.split("\ndef ", 1)[0]
		self.assertIn('"contacts"', helper)
		self.assertIn('"contact_type"', helper)

	def test_the_browser_smoke_reads_the_same_doctype_the_field_links_to(self) -> None:
		"""Si la sonda consultara otro doctype, el rojo señalaría al lugar equivocado."""
		smoke = SMOKE.read_text(encoding="utf-8")
		fixtures = smoke.split("async function resolveFixtureContext", 1)[1].split("\n}", 1)[0]
		self.assertIn('doctype: "NXR Entity"', fixtures)
		self.assertRegex(fixtures, r"entity:\s*entities\?\.\[0\]\?\.name")

	def test_every_demo_idempotency_key_is_unique(self) -> None:
		"""Dos claves iguales devuelven el documento cacheado del primero y el
		segundo registro nunca llega a existir."""
		seeds = SEEDS.read_text(encoding="utf-8")
		keys = re.findall(r'"(nexora-staging-01-[a-z0-9-]+)"', seeds)
		self.assertEqual(sorted(keys), sorted(set(keys)))


if __name__ == "__main__":
	unittest.main()
