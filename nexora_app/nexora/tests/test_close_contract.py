from __future__ import annotations

import json
import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestCloseContract(unittest.TestCase):
	def test_close_module_exists(self) -> None:
		init = APP_ROOT / "close/__init__.py"
		self.assertTrue(init.is_file())

	def test_close_core_exists(self) -> None:
		core = APP_ROOT / "close/core.py"
		self.assertTrue(core.is_file())

	def test_close_service_exists(self) -> None:
		service = APP_ROOT / "close/service.py"
		self.assertTrue(service.is_file())

	def test_monthly_close_doctype_is_defined(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_monthly_close/nxr_monthly_close.json"
		self.assertTrue(path.is_file())
		payload = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual("NXR Monthly Close", payload["name"])

	def test_monthly_close_controller_enforces_boundary(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_monthly_close/nxr_monthly_close.py"
		code = path.read_text(encoding="utf-8")
		self.assertIn("require_service_write", code)
		self.assertIn("on_trash", code)

	def test_monthly_close_has_status_field(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_monthly_close/nxr_monthly_close.json"
		payload = json.loads(path.read_text(encoding="utf-8"))
		field_names = {f["fieldname"] for f in payload["fields"]}
		self.assertIn("status", field_names)
		self.assertIn("project", field_names)
		self.assertIn("close_month", field_names)
		self.assertIn("close_date", field_names)

	def test_an_inert_field_change_does_not_discard_the_calculation(self) -> None:
		"""Los controles de Frappe emiten `change` también al perder el foco, con el mismo
		valor. Pulsar «Calcular» quita el foco del proyecto: el cálculo recién pedido se
		descartaba solo y la huella del motor quedaba vacía."""
		page = APP_ROOT / "nexora/page/nexora_closing/nexora_closing.js"
		source = page.read_text(encoding="utf-8")
		self.assertIn("function fieldChanged(fieldname)", source)
		guard = source.split("function fieldChanged(fieldname) {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn("if (lastValues[fieldname] === current) return false;", guard)
		# Ningún control puede descartar el cálculo sin pasar por la comparación.
		controls = source.split("const controls = {", 1)[1].split("\n\t};", 1)[0]
		for fieldname in ("project", "week_start", "week_end"):
			with self.subTest(field=fieldname):
				line = next(row for row in controls.splitlines() if f'fieldname: "{fieldname}"' in row)
				self.assertIn(f'if (fieldChanged("{fieldname}"))', line)

	def test_a_discarded_calculation_says_who_discarded_it(self) -> None:
		"""Una tarjeta vacía sin motivo no distingue «el motor no respondió» de «algo
		descartó el cálculo» (Capítulo 39)."""
		page = APP_ROOT / "nexora/page/nexora_closing/nexora_closing.js"
		source = page.read_text(encoding="utf-8")
		self.assertIn('function calculationChanged(reason = "unknown")', source)
		body = source.split('function calculationChanged(reason = "unknown") {', 1)[1].split("\n\t}", 1)[0]
		self.assertIn('attr("data-calculation-cleared-by", reason)', body)
		render = source.split("function renderCalculation() {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn('removeAttr("data-calculation-cleared-by")', render)
		# Cada llamada nombra su causa: `unknown` en producción sería un motivo perdido.
		calls = [row.strip() for row in source.splitlines() if "calculationChanged(" in row]
		anonymous = [row for row in calls if "calculationChanged()" in row]
		self.assertEqual([], anonymous, "toda invalidación del cálculo debe nombrar su causa")
		validators = (
			pathlib.Path(nexora.__file__).resolve().parents[2] / "scripts/nexora_browser_validators.mjs"
		)
		self.assertIn("data-calculation-cleared-by", validators.read_text(encoding="utf-8"))
