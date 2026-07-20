from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFINITION = ROOT / "erpnext" / "construcontrol" / "runtime" / "definitions_07.json"
SERVICE = ROOT / "erpnext" / "construcontrol" / "integrations.py"
SETUP = ROOT / "erpnext" / "construcontrol" / "integration_setup.py"
PAGE = ROOT / "erpnext" / "construcontrol" / "page" / "construcontrol_integrations" / "construcontrol_integrations.js"
SHELL = ROOT / "erpnext" / "public" / "js" / "construcontrol_mobile.js"


class IntegrationsContractTest(unittest.TestCase):
	@classmethod
	def setUpClass(cls) -> None:
		cls.definition = json.loads(DEFINITION.read_text(encoding="utf-8"))[0]
		cls.service = SERVICE.read_text(encoding="utf-8")
		cls.setup = SETUP.read_text(encoding="utf-8")
		cls.page = PAGE.read_text(encoding="utf-8")
		cls.shell = SHELL.read_text(encoding="utf-8")
		cls.compact_shell = re.sub(r"\s+", "", cls.shell)

	def test_single_registry_protects_credentials(self) -> None:
		self.assertEqual(self.definition["name"], "CC Integration Registry")
		fields = {row["fieldname"]: row for row in self.definition["fields"]}
		self.assertEqual(fields["credential_secret"]["fieldtype"], "Password")
		self.assertNotIn(
			'"credential_secret":',
			self.service.split("def _safe_row", 1)[1].split("def _validate_endpoint", 1)[0],
		)
		self.assertIn("credential_configured", self.service)

	def test_core_integrations_are_protected_but_can_be_disabled(self) -> None:
		self.assertIn('"is_protected": 1', self.setup)
		self.assertIn("pueden desactivarse, pero no archivarse", self.service)
		self.assertIn("Una integración esencial no puede eliminarse", self.service)

	def test_custom_integrations_can_be_created_archived_and_deleted(self) -> None:
		for function in (
			"create_custom_integration",
			"archive_integration",
			"delete_custom_integration",
			"set_integration_enabled",
			"test_integration",
		):
			self.assertIn(f"def {function}", self.service)
		self.assertIn("ELIMINAR", self.service)

	def test_all_visible_access_is_routed_to_one_center(self) -> None:
		self.assertIn(
			'["INT","Integraciones","⌘",["construcontrol-integrations"]',
			self.compact_shell,
		)
		self.assertEqual(self.compact_shell.count('"construcontrol-integrations"'), 1)
		self.assertIn("Nueva integración", self.page)
		self.assertIn("Integración esencial protegida", self.page)
		self.assertFalse(
			(ROOT / "erpnext" / "public" / "js" / "construcontrol_integrations_bridge.js").exists()
		)


if __name__ == "__main__":
	unittest.main()
