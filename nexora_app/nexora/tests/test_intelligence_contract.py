from __future__ import annotations

import json
import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent
PACKAGE_ROOT = APP_ROOT.parent


class TestIntelligenceContract(unittest.TestCase):
	def test_intelligence_module_files_exist(self) -> None:
		for relative in (
			"intelligence/__init__.py",
			"intelligence/core.py",
			"intelligence/config.py",
			"intelligence/registry.py",
			"intelligence/router.py",
			"intelligence/gateway.py",
			"intelligence/service.py",
		):
			self.assertTrue((APP_ROOT / relative).is_file(), relative)

	def test_no_provider_adapter_is_shipped_yet(self) -> None:
		"""Bloque 1: cero adaptadores reales, cero SDK de proveedor importado."""

		for relative in ("intelligence/core.py", "intelligence/registry.py", "intelligence/router.py",
			"intelligence/gateway.py", "intelligence/service.py"):
			source = (APP_ROOT / relative).read_text(encoding="utf-8")
			for forbidden in ("openai", "anthropic", "import requests", "urllib.request", "httpx"):
				self.assertNotIn(forbidden, source.lower(), f"{relative} referencia {forbidden!r}")

	def test_ai_provider_doctype_is_defined(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_ai_provider/nxr_ai_provider.json"
		self.assertTrue(path.is_file())
		payload = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual("NXR AI Provider", payload["name"])
		self.assertEqual("NEXORA", payload["module"])
		self.assertEqual("DocType", payload["doctype"])

	def test_ai_provider_doctype_has_no_credential_field(self) -> None:
		"""El Bloque 1 no conecta ninguna API key: el DocType no debe ofrecer
		dónde guardar una todavía. Eso es API Key Manager, fuera de alcance."""

		path = APP_ROOT / "nexora/doctype/nxr_ai_provider/nxr_ai_provider.json"
		payload = json.loads(path.read_text(encoding="utf-8"))
		field_names = {field["fieldname"] for field in payload["fields"]}
		for forbidden in ("credential", "credentials", "api_key", "secret", "token"):
			self.assertNotIn(forbidden, field_names)
		fieldtypes = {field["fieldtype"] for field in payload["fields"]}
		self.assertNotIn("Password", fieldtypes)

	def test_ai_provider_doctype_has_expected_fields(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_ai_provider/nxr_ai_provider.json"
		payload = json.loads(path.read_text(encoding="utf-8"))
		field_names = {field["fieldname"] for field in payload["fields"]}
		for expected in ("provider_key", "display_name", "status", "capabilities", "priority"):
			self.assertIn(expected, field_names)

	def test_ai_provider_controller_enforces_boundary(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_ai_provider/nxr_ai_provider.py"
		code = path.read_text(encoding="utf-8")
		self.assertIn("require_service_write", code)
		self.assertIn("on_trash", code)

	def test_ai_provider_doctype_has_init_package_marker(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_ai_provider/__init__.py"
		self.assertTrue(path.is_file())

	def test_permissions_declare_ai_actions(self) -> None:
		source = (APP_ROOT / "permissions.py").read_text(encoding="utf-8")
		self.assertIn('"ai_manage_provider": MANAGER_ROLES,', source)
		self.assertIn('"ai_view_provider": REPORT_EXPORT_ROLES,', source)

	def test_service_gates_every_endpoint_with_require_action(self) -> None:
		source = (APP_ROOT / "intelligence/service.py").read_text(encoding="utf-8")
		whitelisted = source.count("@frappe.whitelist(")
		gated = source.count("require_action(")
		self.assertGreater(whitelisted, 0)
		self.assertEqual(whitelisted, gated)

	def test_service_never_writes_outside_service_write_context(self) -> None:
		source = (APP_ROOT / "intelligence/service.py").read_text(encoding="utf-8")
		self.assertIn("service_write", source)
		self.assertIn("ignore_permissions=True", source)

	def test_service_reuses_shared_audit_and_does_not_duplicate_it(self) -> None:
		source = (APP_ROOT / "intelligence/service.py").read_text(encoding="utf-8")
		self.assertIn("from nexora.financial.db import audit, correlation, parse_payload", source)
		self.assertNotIn('"doctype": "NXR Audit Event"', source)

	def test_block_2_adapter_infrastructure_files_exist(self) -> None:
		for relative in (
			"intelligence/adapters.py",
			"intelligence/providers/__init__.py",
			"intelligence/providers/stub_support.py",
			"intelligence/providers/openai_stub.py",
			"intelligence/providers/anthropic_stub.py",
			"intelligence/providers/gemini_stub.py",
		):
			self.assertTrue((APP_ROOT / relative).is_file(), relative)

	def test_service_was_not_touched_by_block_2(self) -> None:
		"""Bloque 2 no expone ningún endpoint nuevo: no hay todavía ningún
		consumidor real de ``dispatch`` (ERP, chat, UI). Ampliar la superficie
		de `@frappe.whitelist` queda para el bloque que sí lo necesite."""

		source = (APP_ROOT / "intelligence/service.py").read_text(encoding="utf-8")
		self.assertEqual(4, source.count("@frappe.whitelist("))
