"""Pruebas de contrato estático del adaptador SAP.

Verifican estructura real de código/JSON sin ejecutar Frappe: que ningún
secreto se maneja fuera de ``get_password``, que guardar una conexión nunca
llama a SAP, que probar la conexión sí hace una llamada real, que enviar un
documento pasa por idempotencia real y que los permisos server-side están
declarados como corresponde a una integración financiera externa.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]


def function_body(source: str, name: str) -> str:
	match = re.search(rf"\ndef {re.escape(name)}\(.*?\n(?=\n@|\ndef |\Z)", source, flags=re.DOTALL)
	if not match:
		raise AssertionError(f"no se encontró la función {name!r}")
	return match.group(0)


def sap_source() -> str:
	return (APP_ROOT / "integrations/sap.py").read_text(encoding="utf-8")


class TestCredentialsNeverLeak(unittest.TestCase):
	def test_secrets_are_only_ever_read_through_get_password(self) -> None:
		source = sap_source()
		for forbidden in ("audit(", "print(", "frappe.log_error(", "_append_log("):
			for secret in ('"password"', '"client_secret"', '"static_token"'):
				self.assertNotIn(f"{forbidden}{secret}", source)

	def test_connect_connection_never_calls_sap(self) -> None:
		"""Guardar una conexión es una operación distinta de probarla — mismo
		principio que separa `connect_credential` de `test_channel_connection`
		en el canal de WhatsApp."""
		body = function_body(sap_source(), "connect_connection")
		self.assertNotIn("_open_sap_request(", body)
		self.assertNotIn("urlopen(", body)

	def test_test_sap_connection_makes_a_real_http_call_not_a_fake_success(self) -> None:
		body = function_body(sap_source(), "test_sap_connection")
		self.assertIn("_open_sap_request(", body)
		# El éxito solo se asigna dentro del bloque try que hizo la llamada real,
		# nunca antes de intentarla.
		try_at = body.index("try:")
		call_at = body.index("_open_sap_request(")
		success_at = body.index('result_value = "Success"')
		self.assertLess(try_at, call_at)
		self.assertLess(call_at, success_at)


class TestRetryNeverAppliesToAuthOrClientErrors(unittest.TestCase):
	def test_retry_never_applies_to_a_non_retryable_http_status(self) -> None:
		body = function_body(sap_source(), "_open_sap_request")
		self.assertIn("if exc.code not in RETRYABLE_HTTP_STATUS:", body)

	def test_retryable_status_set_never_includes_client_auth_or_permission_errors(self) -> None:
		source = (APP_ROOT / "integrations/sap_core.py").read_text(encoding="utf-8")
		match = re.search(r"RETRYABLE_HTTP_STATUS = frozenset\(\{([^}]*)\}\)", source)
		self.assertIsNotNone(match)
		codes = {int(code.strip()) for code in match.group(1).split(",")}
		for never_retryable in (400, 401, 403, 404):
			self.assertNotIn(never_retryable, codes)

	def test_every_outbound_call_delegates_to_the_shared_retrying_helper(self) -> None:
		source = sap_source()
		for name in ("_fetch_oauth_token", "test_sap_connection", "submit_document"):
			with self.subTest(function=name):
				body = function_body(source, name)
				self.assertIn("_open_sap_request(", body)
				self.assertNotIn("urlopen(", body)


class TestSubmitDocumentUsesRealIdempotency(unittest.TestCase):
	def test_submit_document_starts_and_completes_idempotency(self) -> None:
		body = function_body(sap_source(), "submit_document")
		self.assertIn("start_idempotency(", body)
		self.assertIn("complete_idempotency(", body)
		start_at = body.index("start_idempotency(")
		call_at = body.index("_open_sap_request(")
		complete_at = body.index("complete_idempotency(")
		self.assertLess(start_at, call_at)
		self.assertLess(call_at, complete_at)

	def test_a_cached_idempotent_response_short_circuits_before_any_sap_call(self) -> None:
		body = function_body(sap_source(), "submit_document")
		cached_at = body.index("if cached_response is not None:")
		call_at = body.index("_open_sap_request(")
		self.assertLess(cached_at, call_at)

	def test_a_failed_submission_is_logged_audited_and_completes_idempotency_not_left_stuck(self) -> None:
		"""Un rechazo de SAP nunca debe dejar el registro de idempotencia en
		``Processing`` para siempre: eso bloquearía cualquier reintento futuro
		con la misma clave. Se completa con ``ok: False`` en vez de lanzar."""
		body = function_body(sap_source(), "submit_document")
		self.assertIn("except SapIntegrationError as exc:", body)
		self.assertIn("sap_document_submission_failed", body)
		except_at = body.index("except SapIntegrationError as exc:")
		failure_branch = body[except_at:]
		complete_at = failure_branch.index("complete_idempotency(")
		return_at = failure_branch.index("return result")
		self.assertLess(complete_at, return_at)
		self.assertNotIn("raise", failure_branch[: failure_branch.index("return result")])


class TestEveryWhitelistedWriteRequiresAnAction(unittest.TestCase):
	def test_every_whitelisted_function_requires_an_action(self) -> None:
		source = sap_source()
		for name in (
			"connect_connection",
			"test_sap_connection",
			"submit_document",
			"list_connections",
			"get_sap_summary",
			"list_sap_events",
		):
			with self.subTest(function=name):
				body = function_body(source, name)
				self.assertIn("require_action(", body)

	def test_write_actions_are_whitelisted_post_only(self) -> None:
		source = sap_source()
		for name in (
			"connect_connection",
			"test_sap_connection",
			"submit_document",
			"list_connections",
			"list_sap_events",
		):
			with self.subTest(function=name):
				self.assertIn(f'@frappe.whitelist(methods=["POST"])\ndef {name}(', source)

	def test_get_sap_summary_is_a_read_only_get(self) -> None:
		"""Sin argumentos, sin escritura — mismo patrón que
		``nexora.build_info.get_build_info``."""
		source = sap_source()
		self.assertIn('@frappe.whitelist(methods=["GET"])\ndef get_sap_summary(', source)


class TestPermissionActionsAreDeclaredCorrectly(unittest.TestCase):
	def test_manage_and_submit_actions_map_to_the_expected_role_tiers(self) -> None:
		source = (APP_ROOT / "permissions.py").read_text(encoding="utf-8")
		block = source[
			source.index("ACTION_ROLES") : source.index("ACTION_ROLES")
			+ source[source.index("ACTION_ROLES") :].index("\n}")
		]
		self.assertIn('"manage_sap_connection": ADMINISTRATOR_ONLY_ROLES', block)
		self.assertIn('"submit_sap_document": MANAGER_ROLES', block)
		self.assertIn('"view_sap_connection": REPORT_EXPORT_ROLES', block)


class TestConnectionDocTypeRequiresServiceWrite(unittest.TestCase):
	def test_doctype_forbids_desk_ui_writes_without_the_service_flag(self) -> None:
		source = (APP_ROOT / "nexora/doctype/nxr_sap_connection/nxr_sap_connection.py").read_text(
			encoding="utf-8"
		)
		self.assertIn("require_service_write()", source)

	def test_doctype_forbids_deletion(self) -> None:
		source = (APP_ROOT / "nexora/doctype/nxr_sap_connection/nxr_sap_connection.py").read_text(
			encoding="utf-8"
		)
		self.assertIn("on_trash", source)

	def test_secret_fields_are_password_fieldtype(self) -> None:
		payload = json.loads(
			(APP_ROOT / "nexora/doctype/nxr_sap_connection/nxr_sap_connection.json").read_text(
				encoding="utf-8"
			)
		)
		by_name = {field["fieldname"]: field for field in payload["fields"]}
		for secret_field in ("password", "client_secret", "static_token"):
			self.assertEqual("Password", by_name[secret_field]["fieldtype"], secret_field)

	def test_desk_role_cannot_write_or_create_directly(self) -> None:
		payload = json.loads(
			(APP_ROOT / "nexora/doctype/nxr_sap_connection/nxr_sap_connection.json").read_text(
				encoding="utf-8"
			)
		)
		self.assertTrue(all(not row.get("write") for row in payload["permissions"]))
		self.assertTrue(all(not row.get("create") for row in payload["permissions"]))

	def test_module_is_declared_as_nexora(self) -> None:
		payload = json.loads(
			(APP_ROOT / "nexora/doctype/nxr_sap_connection/nxr_sap_connection.json").read_text(
				encoding="utf-8"
			)
		)
		self.assertEqual("NEXORA", payload["module"])
		self.assertEqual("DocType", payload["doctype"])


class TestOAuthTokenNeverFabricatesASuccessfulToken(unittest.TestCase):
	def test_missing_access_token_in_response_raises_instead_of_continuing(self) -> None:
		body = function_body(sap_source(), "_fetch_oauth_token")
		self.assertIn("if not access_token:", body)
		self.assertIn("raise SapIntegrationError(", body)

	def test_token_is_cached_only_when_the_server_reports_a_positive_ttl(self) -> None:
		body = function_body(sap_source(), "_fetch_oauth_token")
		self.assertIn("oauth_cache_ttl_seconds(", body)
		self.assertIn("if ttl_seconds is not None:", body)


class TestSapSurfacePageRegistration(unittest.TestCase):
	"""Bloque de cierre de producción, Paso 2: antes de este bloque, SAP no
	tenía ninguna página propia — vivía como una tabla más dentro de
	`nexora-integrations`. Mismo checklist de registro real que ya exige
	`TestPageRegistration` en `test_whatsapp_channel_contract.py`."""

	def test_page_files_exist(self) -> None:
		page_dir = APP_ROOT / "nexora/page/nexora_sap"
		self.assertTrue((page_dir / "nexora_sap.json").is_file())
		self.assertTrue((page_dir / "nexora_sap.js").is_file())
		self.assertTrue((page_dir / "__init__.py").is_file())

	def test_registered_in_global_destinations(self) -> None:
		source = (APP_ROOT / "public/js/nexora.js").read_text(encoding="utf-8")
		self.assertIn('href: "/app/nexora-sap"', source)

	def test_registered_in_workspace_shortcuts_and_content(self) -> None:
		source = (APP_ROOT / "nexora/workspace/nexora/nexora.json").read_text(encoding="utf-8")
		self.assertIn('"link_to": "nexora-sap"', source)
		self.assertIn("sap_nexora", source)

	def test_registered_in_shell_navigation(self) -> None:
		source = (APP_ROOT / "public/js/nexora_shell.js").read_text(encoding="utf-8")
		self.assertIn('route: "nexora-sap"', source)

	def test_page_restricted_to_administrative_roles_not_operator_or_viewer(self) -> None:
		payload = json.loads((APP_ROOT / "nexora/page/nexora_sap/nexora_sap.json").read_text(encoding="utf-8"))
		roles = {row["role"] for row in payload["roles"]}
		self.assertNotIn("NEXORA Project Viewer", roles)
		self.assertNotIn("NEXORA Finance Operator", roles)
		self.assertIn("NEXORA Administrator", roles)
		self.assertIn("NEXORA Auditor", roles)

	def test_the_page_calls_the_real_summary_and_events_endpoints_not_a_second_path(self) -> None:
		source = (APP_ROOT / "nexora/page/nexora_sap/nexora_sap.js").read_text(encoding="utf-8")
		for method in (
			"nexora.integrations.sap.get_sap_summary",
			"nexora.integrations.sap.list_connections",
			"nexora.integrations.sap.list_sap_events",
			"nexora.integrations.sap.connect_connection",
			"nexora.integrations.sap.test_sap_connection",
			"nexora.integrations.sap.submit_document",
		):
			with self.subTest(method=method):
				self.assertIn(method, source)


if __name__ == "__main__":
	unittest.main()
