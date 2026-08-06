from __future__ import annotations

import json
import pathlib
import re
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

	def test_service_endpoint_count_is_intentional(self) -> None:
		"""Evita que aparezca un endpoint nuevo sin que se actualice esta
		prueba y la documentación del bloque correspondiente. El número se
		actualiza a propósito en cada bloque que amplía `service.py`: el
		Bloque 1 dejó 4 (`register_provider`, `set_provider_status`,
		`list_providers`, `resolve_capability`); el Bloque 2 no tocó
		`service.py` y por eso siguió en 4 (ver historial de esta prueba,
		antes llamada `test_service_was_not_touched_by_block_2`); el Bloque 3
		añadió 4 más (`update_provider_config`, `set_default_provider`,
		`save_credential`, `list_credential_status`); el Bloque 4 añade 5
		(`check_provider_readiness`, `get_provider_runtime_config`,
		`list_active_providers`, `get_provider_capabilities`,
		`test_provider_connection`); el Bloque 5.2 añade 3 más
		(`run_orchestrated_request`, `preview_routing_decision`,
		`get_provider_usage_summary`), llevando el total a 16."""

		source = (APP_ROOT / "intelligence/service.py").read_text(encoding="utf-8")
		self.assertEqual(16, source.count("@frappe.whitelist("))

	def test_block_3_credential_infrastructure_files_exist(self) -> None:
		for relative in (
			"intelligence/credentials.py",
			"nexora/doctype/nxr_ai_provider_credential/__init__.py",
			"nexora/doctype/nxr_ai_provider_credential/nxr_ai_provider_credential.json",
			"nexora/doctype/nxr_ai_provider_credential/nxr_ai_provider_credential.py",
		):
			self.assertTrue((APP_ROOT / relative).is_file(), relative)

	def test_ai_provider_credential_doctype_is_defined(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_ai_provider_credential/nxr_ai_provider_credential.json"
		payload = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual("NXR AI Provider Credential", payload["name"])
		self.assertEqual("NEXORA", payload["module"])
		self.assertEqual("DocType", payload["doctype"])

	def test_ai_provider_credential_secret_field_is_encrypted(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_ai_provider_credential/nxr_ai_provider_credential.json"
		payload = json.loads(path.read_text(encoding="utf-8"))
		fields_by_name = {field["fieldname"]: field for field in payload["fields"]}
		self.assertIn("secret", fields_by_name)
		self.assertEqual("Password", fields_by_name["secret"]["fieldtype"])
		self.assertEqual(1, fields_by_name["secret"]["reqd"])

	def test_ai_provider_credential_doctype_has_no_reporting_or_export(self) -> None:
		"""Nadie necesita exportar ni reportar sobre esta tabla; menos
		superficie es menos riesgo para un DocType que solo existe para
		guardar secretos cifrados."""

		path = APP_ROOT / "nexora/doctype/nxr_ai_provider_credential/nxr_ai_provider_credential.json"
		payload = json.loads(path.read_text(encoding="utf-8"))
		for permission in payload["permissions"]:
			self.assertEqual(0, permission.get("report", 0), permission)
			self.assertEqual(0, permission.get("export", 0), permission)

	def test_ai_provider_credential_controller_enforces_boundary(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_ai_provider_credential/nxr_ai_provider_credential.py"
		code = path.read_text(encoding="utf-8")
		self.assertIn("require_service_write", code)
		self.assertIn("on_trash", code)

	def test_ai_provider_has_block_3_configuration_fields(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_ai_provider/nxr_ai_provider.json"
		payload = json.loads(path.read_text(encoding="utf-8"))
		field_names = {field["fieldname"] for field in payload["fields"]}
		for expected in (
			"is_default",
			"default_model",
			"timeout_seconds",
			"temperature",
			"max_tokens",
			"cost_hint",
			"validation_state",
			"last_validated_at",
		):
			self.assertIn(expected, field_names)

	def test_ai_provider_still_has_no_credential_field_after_block_3(self) -> None:
		"""La credencial vive en NXR AI Provider Credential, un DocType
		separado — NXR AI Provider en sí mismo sigue sin ninguna, igual que
		en el Bloque 1. Ver test_ai_provider_doctype_has_no_credential_field
		arriba, que ya cubre esto y que este bloque no necesitó tocar."""

		path = APP_ROOT / "nexora/doctype/nxr_ai_provider/nxr_ai_provider.json"
		payload = json.loads(path.read_text(encoding="utf-8"))
		fieldtypes = {field["fieldtype"] for field in payload["fields"]}
		self.assertNotIn("Password", fieldtypes)

	def test_permissions_declare_credential_action_administrator_only(self) -> None:
		source = (APP_ROOT / "permissions.py").read_text(encoding="utf-8")
		self.assertIn('"ai_manage_credential": ADMINISTRATOR_ONLY_ROLES,', source)
		self.assertIn(
			'ADMINISTRATOR_ONLY_ROLES = {"System Manager", "NEXORA Administrator"}', source
		)

	def test_service_never_requests_the_secret_field_in_a_query(self) -> None:
		source = (APP_ROOT / "intelligence/service.py").read_text(encoding="utf-8")
		fields_blocks = re.findall(r"fields\s*=\s*\[[^\]]*\]", source)
		self.assertTrue(fields_blocks)
		for block in fields_blocks:
			self.assertNotIn('"secret"', block, block)

	def test_audit_calls_never_include_the_raw_secret(self) -> None:
		source = (APP_ROOT / "intelligence/service.py").read_text(encoding="utf-8")
		calls = re.findall(r"audit\(\s*\n.*?\n[\t]+\)", source, re.DOTALL)
		self.assertGreaterEqual(len(calls), 6)
		for call in calls:
			self.assertNotIn('"secret": secret', call, call)
			self.assertNotIn("credential.secret", call, call)

	def test_credential_service_functions_are_gated_by_the_administrator_only_action(self) -> None:
		source = (APP_ROOT / "intelligence/service.py").read_text(encoding="utf-8")
		save_credential_source = source[source.index("def save_credential") :]
		self.assertIn('require_action("ai_manage_credential")', save_credential_source)

	def test_block_4_runtime_infrastructure_files_exist(self) -> None:
		for relative in (
			"intelligence/runtime_core.py",
			"intelligence/runtime.py",
			"intelligence/providers/http_support.py",
			"intelligence/providers/openai_compatible_live.py",
			"intelligence/providers/openai_live.py",
			"intelligence/providers/anthropic_live.py",
			"intelligence/providers/gemini_live.py",
			"intelligence/providers/groq_live.py",
			"intelligence/providers/deepseek_live.py",
			"intelligence/providers/mistral_live.py",
			"intelligence/providers/cohere_live.py",
			"intelligence/providers/perplexity_live.py",
			"intelligence/providers/openrouter_live.py",
		):
			self.assertTrue((APP_ROOT / relative).is_file(), relative)

	def test_live_adapters_use_only_the_standard_library_for_networking(self) -> None:
		"""El Bloque 4 sí conecta proveedores reales, pero sin añadir ningún
		SDK ni cliente HTTP de terceros como dependencia — solo ``urllib``,
		ya presente en la biblioteca estándar de Python."""

		forbidden = ("import requests", "import httpx", "import openai\n", "import anthropic\n", "google.generativeai")
		for relative in (
			"intelligence/providers/http_support.py",
			"intelligence/providers/openai_compatible_live.py",
			"intelligence/providers/anthropic_live.py",
			"intelligence/providers/gemini_live.py",
			"intelligence/providers/cohere_live.py",
		):
			source = (APP_ROOT / relative).read_text(encoding="utf-8")
			for token in forbidden:
				self.assertNotIn(token, source, f"{relative} referencia {token!r}")

	def test_live_adapters_declare_the_nine_official_provider_keys(self) -> None:
		source = (APP_ROOT / "intelligence/runtime_core.py").read_text(encoding="utf-8")
		for provider_key in (
			"openai",
			"anthropic",
			"gemini",
			"groq",
			"deepseek",
			"mistral",
			"cohere",
			"perplexity",
			"openrouter",
		):
			self.assertIn(f'"{provider_key}"', source)

	def test_gemini_adapter_authenticates_via_header_not_url(self) -> None:
		"""Una API key en la URL puede terminar en un log de proxy o de
		servidor web; en la cabecera, no (Bloque 4, sección 6)."""

		source = (APP_ROOT / "intelligence/providers/gemini_live.py").read_text(encoding="utf-8")
		self.assertIn("x-goog-api-key", source)
		self.assertNotIn("?key=", source)

	def test_runtime_never_logs_or_returns_the_secret_by_name(self) -> None:
		for relative in ("intelligence/runtime.py", "intelligence/runtime_core.py"):
			source = (APP_ROOT / relative).read_text(encoding="utf-8")
			self.assertNotIn("print(", source)
			self.assertNotIn("frappe.log", source)

	def test_permissions_declare_the_connection_test_action(self) -> None:
		source = (APP_ROOT / "permissions.py").read_text(encoding="utf-8")
		self.assertIn('"ai_test_connection": MANAGER_ROLES,', source)

	def test_connection_test_is_gated_and_audited(self) -> None:
		source = (APP_ROOT / "intelligence/service.py").read_text(encoding="utf-8")
		test_connection_source = source[source.index("def test_provider_connection") :]
		self.assertIn('require_action("ai_test_connection")', test_connection_source)
		self.assertIn("ai_provider_connection_tested", test_connection_source)

	def test_block_1_and_block_2_provider_infrastructure_is_unchanged_by_block_4(self) -> None:
		"""El registro automático de adaptadores simulados (Bloque 2) sigue
		siendo el único mecanismo de auto-registro; el Bloque 4 usa un mapeo
		explícito aparte (``runtime_core.REAL_ADAPTER_CLASSES``), nunca
		``@register_adapter`` — así no compite por las mismas claves con los
		stubs ya registrados."""

		runtime_core_source = (APP_ROOT / "intelligence/runtime_core.py").read_text(encoding="utf-8")
		self.assertNotIn("register_adapter", runtime_core_source)
		for relative in (
			"intelligence/providers/openai_live.py",
			"intelligence/providers/anthropic_live.py",
			"intelligence/providers/gemini_live.py",
		):
			source = (APP_ROOT / relative).read_text(encoding="utf-8")
			self.assertNotIn("register_adapter", source)

	def test_block_5_2_orchestrator_infrastructure_files_exist(self) -> None:
		for relative in (
			"intelligence/orchestrator_core.py",
			"intelligence/orchestrator.py",
			"intelligence/prompt_optimizer.py",
			"nexora/doctype/nxr_ai_usage_event/__init__.py",
			"nexora/doctype/nxr_ai_usage_event/nxr_ai_usage_event.json",
			"nexora/doctype/nxr_ai_usage_event/nxr_ai_usage_event.py",
			"nexora/page/nexora_ai_providers/__init__.py",
			"nexora/page/nexora_ai_providers/nexora_ai_providers.json",
			"nexora/page/nexora_ai_providers/nexora_ai_providers.js",
		):
			self.assertTrue((APP_ROOT / relative).is_file(), relative)

	def test_orchestrator_core_is_frappe_free(self) -> None:
		"""El motor de "regla de oro" (circuito, puntuación, ranking) debe
		poder probarse sin bench/MariaDB, igual que el resto del núcleo
		puro de este módulo (core.py, router.py)."""

		source = (APP_ROOT / "intelligence/orchestrator_core.py").read_text(encoding="utf-8")
		self.assertNotIn("import frappe", source)

	def test_prompt_optimizer_is_frappe_free(self) -> None:
		source = (APP_ROOT / "intelligence/prompt_optimizer.py").read_text(encoding="utf-8")
		self.assertNotIn("import frappe", source)

	def test_usage_event_doctype_is_append_only_and_unwritable_directly(self) -> None:
		"""Igual que NXR Audit Event: nadie tiene permiso de crear/editar
		filas por la UI estándar; solo el servicio, vía
		``ignore_permissions=True`` dentro de un contexto de escritura
		autorizado."""

		path = APP_ROOT / "nexora/doctype/nxr_ai_usage_event/nxr_ai_usage_event.json"
		payload = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual("NXR AI Usage Event", payload["name"])
		self.assertEqual("NEXORA", payload["module"])
		for permission in payload["permissions"]:
			self.assertEqual(0, permission.get("write", 0), permission)
			self.assertEqual(0, permission.get("create", 0), permission)

		code = (APP_ROOT / "nexora/doctype/nxr_ai_usage_event/nxr_ai_usage_event.py").read_text(encoding="utf-8")
		self.assertIn("require_service_write", code)

	def test_orchestrator_execute_uses_the_existing_gateway_and_runtime_not_a_parallel_path(self) -> None:
		"""El Bloque 5.2 pidió explícitamente no duplicar lógica: el bucle de
		reintento debe apoyarse en ``gateway.build_registry`` (Bloque 1) y
		``runtime.build_ready_adapter`` (Bloque 4), no reimplementar su
		propio cliente de proveedores."""

		source = (APP_ROOT / "intelligence/orchestrator.py").read_text(encoding="utf-8")
		self.assertIn("build_registry", source)
		self.assertIn("build_ready_adapter", source)

	def test_new_endpoints_are_gated_and_never_return_the_secret(self) -> None:
		source = (APP_ROOT / "intelligence/service.py").read_text(encoding="utf-8")
		for function_name, action in (
			("run_orchestrated_request", "ai_test_connection"),
			("preview_routing_decision", "ai_view_provider"),
			("get_provider_usage_summary", "ai_view_provider"),
		):
			start = source.index(f"def {function_name}")
			end = source.index("\ndef ", start + 1) if "\ndef " in source[start + 1 :] else len(source)
			body = source[start:end]
			self.assertIn(f'require_action("{action}")', body, function_name)
			self.assertNotIn("secret", body, function_name)

	def test_ai_provider_has_block_5_2_health_fields(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_ai_provider/nxr_ai_provider.json"
		payload = json.loads(path.read_text(encoding="utf-8"))
		field_names = {field["fieldname"] for field in payload["fields"]}
		for expected in (
			"circuit_state",
			"consecutive_failures",
			"degraded_until",
			"last_outcome_at",
			"last_error_kind",
		):
			self.assertIn(expected, field_names)

	def test_ai_providers_page_is_reachable_from_workspace_and_top_nav(self) -> None:
		workspace = json.loads(
			(APP_ROOT / "nexora/workspace/nexora/nexora.json").read_text(encoding="utf-8")
		)
		self.assertIn(
			"nexora-ai-providers", [shortcut["link_to"] for shortcut in workspace["shortcuts"]]
		)
		nav_source = (APP_ROOT / "public/js/nexora.js").read_text(encoding="utf-8")
		self.assertIn("/app/nexora-ai-providers", nav_source)
