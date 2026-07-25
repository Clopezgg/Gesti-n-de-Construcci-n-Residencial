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
