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
			"create_field_mapping",
			"update_field_mapping",
			"deactivate_field_mapping",
			"list_field_mappings",
			"pull_document",
			"list_inbound_records",
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
			"create_field_mapping",
			"update_field_mapping",
			"deactivate_field_mapping",
			"list_field_mappings",
			"pull_document",
			"list_inbound_records",
		):
			with self.subTest(function=name):
				self.assertIn(f'@frappe.whitelist(methods=["POST"])\ndef {name}(', source)

	def test_mapping_writes_never_call_sap_directly(self) -> None:
		"""Guardar/actualizar/desactivar un mapeo es configuración pura — igual
		que `connect_connection`, nunca dispara una llamada real a SAP."""
		source = sap_source()
		for name in ("create_field_mapping", "update_field_mapping", "deactivate_field_mapping"):
			with self.subTest(function=name):
				body = function_body(source, name)
				self.assertNotIn("_open_sap_request(", body)

	def test_mapping_writes_are_audited_and_deletion_is_never_used(self) -> None:
		source = sap_source()
		for name in ("create_field_mapping", "update_field_mapping", "deactivate_field_mapping"):
			with self.subTest(function=name):
				body = function_body(source, name)
				self.assertIn("audit(", body)
				self.assertNotIn("delete_doc", body)

	def test_deactivate_sets_active_false_not_a_delete(self) -> None:
		body = function_body(sap_source(), "deactivate_field_mapping")
		self.assertIn("doc.active = 0", body)

	def test_get_sap_summary_is_a_read_only_get(self) -> None:
		"""Sin argumentos, sin escritura — mismo patrón que
		``nexora.build_info.get_build_info``."""
		source = sap_source()
		self.assertIn('@frappe.whitelist(methods=["GET"])\ndef get_sap_summary(', source)

	def test_pull_document_uses_real_idempotency_and_never_writes_a_business_doctype(self) -> None:
		"""SAP → NEXORA aterriza en `NXR SAP Inbound Record`, nunca en un
		DocType de negocio real — promover un registro entrante es una
		decisión humana separada, no algo que este adaptador haga solo."""
		body = function_body(sap_source(), "pull_document")
		self.assertIn("start_idempotency(", body)
		self.assertIn("complete_idempotency(", body)
		self.assertIn("INBOUND_DOCTYPE", body)
		for forbidden_doctype_hint in ("NXR Operation", "NXR Contract", "NXR Fund"):
			self.assertNotIn(forbidden_doctype_hint, body)

	def test_pull_document_is_audited_on_success_and_on_failure(self) -> None:
		body = function_body(sap_source(), "pull_document")
		self.assertIn('"sap_document_pulled"', body)
		self.assertIn('"sap_document_pull_failed"', body)

	def test_pull_document_detects_duplicates_by_comparing_the_actual_payload(self) -> None:
		"""Detección de cambios real: compara el payload anterior contra el
		nuevo, nunca asume "cambió" o "no cambió" sin comparar."""
		body = function_body(sap_source(), "pull_document")
		self.assertIn('"Duplicate" if previous_payload_json == new_payload_json else "Updated"', body)


class TestPermissionActionsAreDeclaredCorrectly(unittest.TestCase):
	def test_manage_and_submit_actions_map_to_the_expected_role_tiers(self) -> None:
		source = (APP_ROOT / "permissions.py").read_text(encoding="utf-8")
		block = source[
			source.index("ACTION_ROLES") : source.index("ACTION_ROLES")
			+ source[source.index("ACTION_ROLES") :].index("\n}")
		]
		self.assertIn('"manage_sap_connection": ADMINISTRATOR_ONLY_ROLES', block)
		self.assertIn('"submit_sap_document": MANAGER_ROLES', block)
		self.assertIn('"sync_sap_document": MANAGER_ROLES', block)
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


class TestFieldMappingDocTypeRequiresServiceWrite(unittest.TestCase):
	"""Bloque de cierre masivo: capa real de mapeo NEXORA→SAP, mismo patrón
	de gobernanza que ya usa `NXR SAP Connection` — nunca se borra, nunca se
	escribe desde el Desk directamente."""

	def test_doctype_forbids_desk_ui_writes_without_the_service_flag(self) -> None:
		source = (APP_ROOT / "nexora/doctype/nxr_sap_field_mapping/nxr_sap_field_mapping.py").read_text(
			encoding="utf-8"
		)
		self.assertIn("require_service_write()", source)

	def test_doctype_forbids_deletion(self) -> None:
		source = (APP_ROOT / "nexora/doctype/nxr_sap_field_mapping/nxr_sap_field_mapping.py").read_text(
			encoding="utf-8"
		)
		self.assertIn("on_trash", source)

	def test_version_increments_only_on_a_substantive_change(self) -> None:
		source = (APP_ROOT / "nexora/doctype/nxr_sap_field_mapping/nxr_sap_field_mapping.py").read_text(
			encoding="utf-8"
		)
		self.assertIn("_VERSIONED_FIELDS", source)
		self.assertIn("self.version = (self.version or 1) + 1", source)

	def test_desk_role_cannot_write_or_create_directly(self) -> None:
		payload = json.loads(
			(APP_ROOT / "nexora/doctype/nxr_sap_field_mapping/nxr_sap_field_mapping.json").read_text(
				encoding="utf-8"
			)
		)
		self.assertTrue(all(not row.get("write") for row in payload["permissions"]))
		self.assertTrue(all(not row.get("create") for row in payload["permissions"]))

	def test_module_is_declared_as_nexora(self) -> None:
		payload = json.loads(
			(APP_ROOT / "nexora/doctype/nxr_sap_field_mapping/nxr_sap_field_mapping.json").read_text(
				encoding="utf-8"
			)
		)
		self.assertEqual("NEXORA", payload["module"])
		self.assertEqual("DocType", payload["doctype"])

	def test_connection_field_links_to_the_real_connection_doctype(self) -> None:
		payload = json.loads(
			(APP_ROOT / "nexora/doctype/nxr_sap_field_mapping/nxr_sap_field_mapping.json").read_text(
				encoding="utf-8"
			)
		)
		by_name = {field["fieldname"]: field for field in payload["fields"]}
		self.assertEqual("Link", by_name["connection"]["fieldtype"])
		self.assertEqual("NXR SAP Connection", by_name["connection"]["options"])


class TestInboundRecordDocTypeRequiresServiceWrite(unittest.TestCase):
	"""SAP → NEXORA aterriza aquí — mismo patrón de gobernanza que
	`NXR SAP Connection`/`NXR SAP Field Mapping`: nunca se borra, nunca se
	escribe desde el Desk directamente."""

	def test_doctype_forbids_desk_ui_writes_without_the_service_flag(self) -> None:
		source = (APP_ROOT / "nexora/doctype/nxr_sap_inbound_record/nxr_sap_inbound_record.py").read_text(
			encoding="utf-8"
		)
		self.assertIn("require_service_write()", source)

	def test_doctype_forbids_deletion(self) -> None:
		source = (APP_ROOT / "nexora/doctype/nxr_sap_inbound_record/nxr_sap_inbound_record.py").read_text(
			encoding="utf-8"
		)
		self.assertIn("on_trash", source)

	def test_desk_role_cannot_write_or_create_directly(self) -> None:
		payload = json.loads(
			(APP_ROOT / "nexora/doctype/nxr_sap_inbound_record/nxr_sap_inbound_record.json").read_text(
				encoding="utf-8"
			)
		)
		self.assertTrue(all(not row.get("write") for row in payload["permissions"]))
		self.assertTrue(all(not row.get("create") for row in payload["permissions"]))

	def test_module_is_declared_as_nexora(self) -> None:
		payload = json.loads(
			(APP_ROOT / "nexora/doctype/nxr_sap_inbound_record/nxr_sap_inbound_record.json").read_text(
				encoding="utf-8"
			)
		)
		self.assertEqual("NEXORA", payload["module"])
		self.assertEqual("DocType", payload["doctype"])

	def test_connection_field_links_to_the_real_connection_doctype(self) -> None:
		payload = json.loads(
			(APP_ROOT / "nexora/doctype/nxr_sap_inbound_record/nxr_sap_inbound_record.json").read_text(
				encoding="utf-8"
			)
		)
		by_name = {field["fieldname"]: field for field in payload["fields"]}
		self.assertEqual("Link", by_name["connection"]["fieldtype"])
		self.assertEqual("NXR SAP Connection", by_name["connection"]["options"])


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
		payload = json.loads(
			(APP_ROOT / "nexora/page/nexora_sap/nexora_sap.json").read_text(encoding="utf-8")
		)
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
			"nexora.integrations.sap.create_field_mapping",
			"nexora.integrations.sap.update_field_mapping",
			"nexora.integrations.sap.deactivate_field_mapping",
			"nexora.integrations.sap.list_field_mappings",
			"nexora.integrations.sap.pull_document",
			"nexora.integrations.sap.list_inbound_records",
		):
			with self.subTest(method=method):
				self.assertIn(method, source)

	def test_mapeos_tab_renders_a_real_table_not_the_old_placeholder_notice(self) -> None:
		"""Antes de este bloque, `renderMapeos()` solo mostraba un aviso
		estático diciendo que no existía catálogo de mapeos. Ahora existe un
		catálogo real (`NXR SAP Field Mapping`) — la pestaña debe mostrar una
		tabla real y las acciones de agregar/editar/desactivar, no volver a
		caer en el aviso de "todavía no existe"."""
		source = (APP_ROOT / "nexora/page/nexora_sap/nexora_sap.js").read_text(encoding="utf-8")
		self.assertIn("mappingRowHtml", source)
		self.assertIn("data-add-mapping", source)
		self.assertIn("data-edit-mapping", source)
		self.assertIn("data-deactivate-mapping", source)
		self.assertNotIn("todavía no tiene un catálogo central de mapeos", source)

	def test_sincronizacion_tab_shows_both_real_directions_not_only_push(self) -> None:
		"""Antes de este bloque, «Sincronización» solo resumía el envío
		NEXORA → SAP; ahora también existe SAP → NEXORA real (`pull_document`)
		— la pestaña debe mostrar ambas direcciones, nunca solo la mitad."""
		source = (APP_ROOT / "nexora/page/nexora_sap/nexora_sap.js").read_text(encoding="utf-8")
		self.assertIn("inboundRowHtml", source)
		self.assertIn("openPullDocumentDialog", source)
		self.assertIn("Consultar documento", source)

	def test_auditoria_tab_has_a_real_label_for_every_event_type_the_backend_emits(self) -> None:
		"""Bloque 184: `EVENT_LABELS` se quedó fijo en los cuatro eventos
		originales mientras `sap.py` ya emitía cuatro más (mapeos y sync) —
		esos eventos caían al valor crudo del backend en vez de un rótulo
		real. Esta prueba falla si vuelve a desalinearse: cada evento que
		`_ALL_EVENT_TYPES` declara en el backend debe tener una traducción
		real en el frontend."""
		backend_source = (APP_ROOT / "integrations/sap.py").read_text(encoding="utf-8")
		frontend_source = (APP_ROOT / "nexora/page/nexora_sap/nexora_sap.js").read_text(encoding="utf-8")
		event_types_block = backend_source[
			backend_source.index("_DOCUMENT_EVENT_TYPES = (") : backend_source.index(
				"@frappe.whitelist", backend_source.index("_ALL_EVENT_TYPES = (")
			)
		]
		declared_event_types = set(re.findall(r'"(sap_[a-z_]+)"', event_types_block))
		labels_block = frontend_source[
			frontend_source.index("EVENT_LABELS") : frontend_source.index("function auditRowHtml")
		]
		self.assertEqual(8, len(declared_event_types), sorted(declared_event_types))
		for event_type in declared_event_types:
			with self.subTest(event_type=event_type):
				self.assertIn(event_type, labels_block)

	def test_auditoria_tab_shows_the_real_correlation_id_not_only_the_event(self) -> None:
		"""Trazabilidad real (Objetivo 3/7): la bitácora de auditoría ya
		devolvía `correlation_id` desde el backend, pero la tabla nunca lo
		mostraba — sin verlo, nadie puede correlacionar de verdad un evento
		SAP con la operación real de NEXORA que lo disparó."""
		source = (APP_ROOT / "nexora/page/nexora_sap/nexora_sap.js").read_text(encoding="utf-8")
		self.assertIn("row.correlation_id", source)


if __name__ == "__main__":
	unittest.main()
