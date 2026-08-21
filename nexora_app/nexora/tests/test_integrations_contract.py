from __future__ import annotations

import json
import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestIntegrationsContract(unittest.TestCase):
	def test_integrations_module_exists(self) -> None:
		init = APP_ROOT / "integrations/__init__.py"
		self.assertTrue(init.is_file())

	def test_integrations_core_exists(self) -> None:
		core = APP_ROOT / "integrations/core.py"
		self.assertTrue(core.is_file())

	def test_integrations_service_exists(self) -> None:
		service = APP_ROOT / "integrations/service.py"
		self.assertTrue(service.is_file())

	def test_integration_doctype_is_defined(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_integration/nxr_integration.json"
		self.assertTrue(path.is_file())
		payload = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual("NXR Integration", payload["name"])

	def test_integration_controller_enforces_boundary(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_integration/nxr_integration.py"
		code = path.read_text(encoding="utf-8")
		self.assertIn("require_service_write", code)
		self.assertIn("on_trash", code)

	def test_integration_log_is_table(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_integration_log/nxr_integration_log.json"
		self.assertTrue(path.is_file())
		payload = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual("NXR Integration Log", payload["name"])
		self.assertEqual(1, payload["istable"])

	def test_integration_log_has_level_field(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_integration_log/nxr_integration_log.json"
		payload = json.loads(path.read_text(encoding="utf-8"))
		field_names = {f["fieldname"] for f in payload["fields"]}
		self.assertIn("level", field_names)
		self.assertIn("message", field_names)
		self.assertIn("timestamp", field_names)

	def test_page_files_exist(self) -> None:
		"""Hallazgo real de auditoría (bloque posterior al 58): siete funciones
		whitelisted, reales y con lógica detrás, entre `integrations.service` y
		`integrations.sap`, no tenían ningún llamador en todo el repositorio —
		ni página, ni ningún otro `.js`. GP-04/NXR-INT-001 nunca tuvo un punto
		de entrada real para registrar una integración o conectar SAP."""
		page_dir = APP_ROOT / "nexora/page/nexora_integrations"
		self.assertTrue((page_dir / "nexora_integrations.json").is_file())
		self.assertTrue((page_dir / "nexora_integrations.js").is_file())
		self.assertTrue((page_dir / "__init__.py").is_file())

	def test_page_calls_the_real_service_methods(self) -> None:
		"""Cierre de producción, Paso 2: las conexiones SAP se movieron a su
		propia página (`nexora-sap`, ver `TestSapSurfacePageRegistration` en
		`test_sap_integration_contract.py`) — esta pantalla ya solo gestiona el
		registro genérico REST/SOAP/Webhook/Custom."""
		source = (APP_ROOT / "nexora/page/nexora_integrations/nexora_integrations.js").read_text(
			encoding="utf-8"
		)
		for method in (
			"nexora.integrations.service.register_integration",
			"nexora.integrations.service.test_connection",
			"nexora.integrations.service.list_integrations",
		):
			self.assertIn(method, source)

	def test_page_points_to_the_dedicated_sap_surface_instead_of_duplicating_it(self) -> None:
		source = (APP_ROOT / "nexora/page/nexora_integrations/nexora_integrations.js").read_text(
			encoding="utf-8"
		)
		self.assertIn("/app/nexora-sap", source)
		self.assertNotIn("nexora.integrations.sap.", source)

	def test_registering_an_integration_is_audited(self) -> None:
		"""Bloque 167 (Paso 5 del cierre maestro, formularios nativos): `test_connection`,
		en este mismo archivo, ya audita cada intento de conexión (comentario propio cita
		el Bloque 22), pero registrar la integración en sí —incluidas sus credenciales—
		nunca dejó rastro en `NXR Audit Event`.

		Lee el archivo como texto, sin importar el módulo: `frappe` no está instalado en
		este job de CI (mismo motivo por el que el resto de esta clase ya usa
		`.read_text()`, nunca un `import` real de `nexora.integrations.service`)."""
		source = (APP_ROOT / "integrations/service.py").read_text(encoding="utf-8")
		function_source = source.split("def register_integration(", 1)[1].split("\n@frappe.whitelist", 1)[0]
		self.assertIn("audit(", function_source)
