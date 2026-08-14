"""Pruebas de contrato estático del canal WhatsApp (Bloque 21, NXR-INT-0008).

Verifican estructura real de código/JSON sin ejecutar Frappe: que la firma se
verifica antes de confiar en cualquier payload, que las credenciales nunca se
registran en texto plano, que los DocTypes nuevos exigen escritura por
servicio, y que la página administrativa está registrada donde el invariante
de gobernanza (Bloque 17) exige.
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


class TestWebhookSecurity(unittest.TestCase):
	def source(self) -> str:
		return (APP_ROOT / "conversation/channels/whatsapp.py").read_text(encoding="utf-8")

	def test_webhook_is_the_only_guest_accessible_endpoint_in_the_module(self) -> None:
		source = self.source()
		self.assertEqual(
			1, len(re.findall(r"^@frappe\.whitelist\(allow_guest=True", source, flags=re.MULTILINE))
		)
		self.assertIn(
			'@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])  # nosemgrep\ndef webhook()', source
		)

	def test_post_branch_verifies_the_signature_before_parsing_the_body(self) -> None:
		source = self.source()
		body = function_body(source, "webhook")
		verify_at = body.index("verify_signature(")
		parse_at = body.index("frappe.parse_json(")
		self.assertLess(verify_at, parse_at, "la firma debe verificarse antes de confiar en el payload")

	def test_webhook_never_trusts_a_client_supplied_verify_token_without_comparing_the_stored_one(
		self,
	) -> None:
		source = self.source()
		body = function_body(source, "webhook")
		self.assertIn(
			'extract_verification_challenge(frappe.local.form_dict, credential["verify_token"])', body
		)

	def test_unconfigured_channel_rejects_both_get_and_post_before_touching_meta(self) -> None:
		source = self.source()
		body = function_body(source, "webhook")
		self.assertEqual(2, body.count("Canal de WhatsApp no configurado"))


class TestCredentialsNeverLeak(unittest.TestCase):
	def test_no_function_returns_or_logs_a_raw_secret(self) -> None:
		source = (APP_ROOT / "conversation/channels/whatsapp.py").read_text(encoding="utf-8")
		# Los tres secretos solo deben pasar por get_password(); nunca deben
		# aparecer como valor literal en un dict devuelto a un llamador salvo
		# dentro de _active_credential (que sí necesita tenerlos en memoria
		# para llamar a la Graph API) o al construir el propio payload de
		# guardado (que es exactamente lo que el usuario acaba de escribir).
		self.assertEqual(4, source.count(".get_password("))
		for forbidden in ("audit(", "print(", "frappe.log_error("):
			self.assertNotIn(f'{forbidden}"app_secret"', source)
			self.assertNotIn(f'{forbidden}"access_token"', source)

	def test_connect_credential_never_calls_the_real_api(self) -> None:
		"""Guardar una credencial es una operación distinta de probarla — mismo
		principio que separó `save_credential`/`test_provider_connection` en el
		módulo de IA (Bloque 3)."""
		source = (APP_ROOT / "conversation/channels/whatsapp.py").read_text(encoding="utf-8")
		body = function_body(source, "connect_credential")
		self.assertNotIn("_graph_get(", body)
		self.assertNotIn("_graph_post_json(", body)

	def test_test_channel_connection_makes_a_real_graph_api_call_not_a_fake_success(self) -> None:
		source = (APP_ROOT / "conversation/channels/whatsapp.py").read_text(encoding="utf-8")
		body = function_body(source, "test_channel_connection")
		self.assertIn("_graph_get(", body)
		self.assertNotIn('"last_test_result", "Success")', body)


class TestChannelDocTypesRequireServiceWrite(unittest.TestCase):
	def test_both_new_doctypes_forbid_desk_ui_writes_without_the_service_flag(self) -> None:
		for doctype_dir in ("nxr_channel_credential", "nxr_channel_account"):
			path = APP_ROOT / f"nexora/doctype/{doctype_dir}/{doctype_dir}.py"
			source = path.read_text(encoding="utf-8")
			self.assertIn("require_service_write()", source, doctype_dir)

	def test_credential_doctype_forbids_deletion(self) -> None:
		source = (APP_ROOT / "nexora/doctype/nxr_channel_credential/nxr_channel_credential.py").read_text(
			encoding="utf-8"
		)
		self.assertIn("on_trash", source)

	def test_account_doctype_rejects_a_duplicate_active_link_for_the_same_number(self) -> None:
		source = (APP_ROOT / "nexora/doctype/nxr_channel_account/nxr_channel_account.py").read_text(
			encoding="utf-8"
		)
		self.assertIn("Ya existe una cuenta activa", source)

	def test_credential_fields_that_hold_secrets_are_password_fieldtype(self) -> None:
		payload = json.loads(
			(APP_ROOT / "nexora/doctype/nxr_channel_credential/nxr_channel_credential.json").read_text(
				encoding="utf-8"
			)
		)
		by_name = {field["fieldname"]: field for field in payload["fields"]}
		for secret_field in ("app_secret", "access_token", "verify_token"):
			self.assertEqual("Password", by_name[secret_field]["fieldtype"], secret_field)

	def test_message_doctype_requires_service_write_and_forbids_desk_ui_create(self) -> None:
		"""NXR-INT-0008 (estados de entrega): el registro real de un mensaje
		saliente y su estado real de Meta no es algo que nadie deba crear ni
		editar a mano desde el Desk — mismo candado que ya protege
		`NXR Conversation Message` (Bloque 18): 0 en `create`/`write` a nivel de
		permiso, más `require_service_write()` en el controlador como segunda
		barrera real, no solo declarada."""
		source = (APP_ROOT / "nexora/doctype/nxr_channel_message/nxr_channel_message.py").read_text(
			encoding="utf-8"
		)
		self.assertIn("require_service_write()", source)
		payload = json.loads(
			(APP_ROOT / "nexora/doctype/nxr_channel_message/nxr_channel_message.json").read_text(
				encoding="utf-8"
			)
		)
		self.assertTrue(all(not row.get("create") for row in payload["permissions"]))
		self.assertTrue(all(not row.get("write") for row in payload["permissions"]))
		by_name = {field["fieldname"]: field for field in payload["fields"]}
		self.assertTrue(by_name["external_message_id"].get("unique"))


class TestOutboundDeliveryTracking(unittest.TestCase):
	"""NXR-INT-0008: un mensaje saliente real queda registrado bajo su id real
	de Meta, y una actualización real de estado (`value.statuses`) se aplica a
	ese registro real — antes se reconocía y se descartaba en silencio."""

	def source(self) -> str:
		return (APP_ROOT / "conversation/channels/whatsapp.py").read_text(encoding="utf-8")

	def test_sending_a_message_records_the_real_meta_message_id(self) -> None:
		body = function_body(self.source(), "_send_text_message")
		self.assertIn("_record_sent_message(", body)
		self.assertIn('response.get("messages")', body)

	def test_the_webhook_applies_real_status_updates_not_only_messages(self) -> None:
		body = function_body(self.source(), "webhook")
		self.assertIn("extract_status_updates(", body)
		self.assertIn("_process_status_update(", body)

	def test_status_update_never_invents_a_status_outside_the_known_set(self) -> None:
		body = function_body(self.source(), "_process_status_update")
		self.assertIn("_STATUS_LABELS.get(", body)

	def test_a_failed_status_never_overwrites_error_detail_with_nothing(self) -> None:
		body = function_body(self.source(), "_process_status_update")
		self.assertIn('if label == "Failed" and update.get("error_detail"):', body)


class TestOutboundGraphCallsRetryOnce(unittest.TestCase):
	"""NXR-INT-0008: un solo reintento inmediato ante un error transitorio de
	Meta — mismo criterio que `intelligence.orchestrator_core.
	should_retry_same_provider` ya certificó para el gateway de IA (nunca para
	errores de autenticación o de solicitud mal formada)."""

	def source(self) -> str:
		return (APP_ROOT / "conversation/channels/whatsapp.py").read_text(encoding="utf-8")

	def test_graph_get_and_post_delegate_to_the_shared_retrying_helper(self) -> None:
		source = self.source()
		get_body = function_body(source, "_graph_get")
		post_body = function_body(source, "_graph_post_json")
		self.assertIn("_open_graph_request(", get_body)
		self.assertIn("_open_graph_request(", post_body)
		# Ninguna de las dos vuelve a llamar a `urlopen` directamente — toda
		# la lógica de reintento vive en un único lugar real.
		self.assertNotIn("urlopen(", get_body)
		self.assertNotIn("urlopen(", post_body)

	def test_retry_never_applies_to_a_non_retryable_http_status(self) -> None:
		body = function_body(self.source(), "_open_graph_request")
		self.assertIn("if exc.code not in _RETRYABLE_HTTP_STATUS:", body)

	def test_retryable_status_set_never_includes_client_auth_or_permission_errors(self) -> None:
		source = self.source()
		match = re.search(r"_RETRYABLE_HTTP_STATUS = frozenset\(\{([^}]*)\}\)", source)
		self.assertIsNotNone(match)
		codes = {int(code.strip()) for code in match.group(1).split(",")}
		for never_retryable in (400, 401, 403, 404):
			self.assertNotIn(never_retryable, codes)


class TestAdministrativeActionsAreAudited(unittest.TestCase):
	"""Bloque 22: conectar/probar una credencial de canal o decidir qué usuario
	real actúa detrás de un número externo es tan sensible como cualquier otra
	acción financiera — debe quedar en la misma bitácora cruzada
	(`NXR Audit Event`), no solo en el propio doctype."""

	def source(self) -> str:
		return (APP_ROOT / "conversation/channels/whatsapp.py").read_text(encoding="utf-8")

	def test_every_administrative_action_calls_the_real_audit_trail(self) -> None:
		source = self.source()
		for name in (
			"connect_credential",
			"test_channel_connection",
			"deactivate_credential",
			"link_channel_account",
			"revoke_channel_account",
		):
			with self.subTest(function=name):
				body = function_body(source, name)
				self.assertIn("audit(", body)


class TestDirectMessageSendingForOtherModules(unittest.TestCase):
	"""Bloque 23: `notifications.service` necesita enviar un WhatsApp directo sin
	depender de los internos privados de este módulo (mismo principio de capas
	que ``financial.context.service_write``)."""

	def source(self) -> str:
		return (APP_ROOT / "conversation/channels/whatsapp.py").read_text(encoding="utf-8")

	def test_resolve_external_id_for_user_does_a_real_reverse_lookup(self) -> None:
		source = self.source()
		body = function_body(source, "resolve_external_id_for_user")
		self.assertIn("ACCOUNT_DOCTYPE", body)
		self.assertIn('"status": "Active"', body)

	def test_send_direct_message_never_returns_a_fabricated_success(self) -> None:
		source = self.source()
		body = function_body(source, "send_direct_message")
		self.assertIn("_active_credential()", body)
		self.assertIn("raise WhatsAppChannelError(", body)
		self.assertIn("_send_text_message(credential, to, body)", body)

	def test_send_direct_message_is_not_itself_whitelisted(self) -> None:
		"""Cada llamador (p. ej. `notifications.service`) decide su propio
		permiso — esta función no debe exponerse directamente como endpoint."""
		source = self.source()
		self.assertNotIn(
			"@frappe.whitelist", source[: source.index("\ndef send_direct_message(")].splitlines()[-1]
		)


class TestPermissionActionsAreAdministratorOnly(unittest.TestCase):
	def test_manage_actions_map_to_administrator_only_roles(self) -> None:
		source = (APP_ROOT / "permissions.py").read_text(encoding="utf-8")
		block = source[
			source.index("ACTION_ROLES") : source.index("ACTION_ROLES")
			+ source[source.index("ACTION_ROLES") :].index("\n}")
		]
		self.assertIn('"manage_channel_credential": ADMINISTRATOR_ONLY_ROLES', block)
		self.assertIn('"manage_channel_account": ADMINISTRATOR_ONLY_ROLES', block)

	def test_every_whitelisted_write_function_requires_an_action(self) -> None:
		source = (APP_ROOT / "conversation/channels/whatsapp.py").read_text(encoding="utf-8")
		for name in (
			"connect_credential",
			"test_channel_connection",
			"deactivate_credential",
			"link_channel_account",
			"revoke_channel_account",
		):
			with self.subTest(function=name):
				body = function_body(source, name)
				self.assertIn("require_action(", body)


class TestPageRegistration(unittest.TestCase):
	def test_page_files_exist(self) -> None:
		page_dir = APP_ROOT / "nexora/page/nexora_conversation_channels"
		self.assertTrue((page_dir / "nexora_conversation_channels.json").is_file())
		self.assertTrue((page_dir / "nexora_conversation_channels.js").is_file())
		self.assertTrue((page_dir / "__init__.py").is_file())

	def test_registered_in_global_destinations(self) -> None:
		source = (APP_ROOT / "public/js/nexora.js").read_text(encoding="utf-8")
		self.assertIn('href: "/app/nexora-conversation-channels"', source)

	def test_registered_in_workspace_shortcuts_and_content(self) -> None:
		source = (APP_ROOT / "nexora/workspace/nexora/nexora.json").read_text(encoding="utf-8")
		self.assertIn('"link_to": "nexora-conversation-channels"', source)
		self.assertIn("canales_nexora", source)

	def test_registered_in_shell_navigation(self) -> None:
		"""Hallazgo real de auditoría: el workspace legado y la lista de
		accesos de la PWA (`nexora.js`) no son la navegación que ve un
		usuario real desde que la carcasa (`nexora_shell.js`) reemplazó la
		barra lateral de Frappe — ninguno de los dos abre esa barra. Sin
		esta entrada en `SECTIONS`, la pantalla de WhatsApp solo era
		alcanzable tecleando la URL a mano."""
		source = (APP_ROOT / "public/js/nexora_shell.js").read_text(encoding="utf-8")
		self.assertIn('route: "nexora-conversation-channels"', source)

	def test_page_restricted_to_administrative_roles_not_project_viewer(self) -> None:
		payload = json.loads(
			(
				APP_ROOT / "nexora/page/nexora_conversation_channels/nexora_conversation_channels.json"
			).read_text(encoding="utf-8")
		)
		roles = {row["role"] for row in payload["roles"]}
		self.assertNotIn("NEXORA Project Viewer", roles)
		self.assertIn("NEXORA Administrator", roles)


class TestDispatchAttachmentExtension(unittest.TestCase):
	"""El canal de texto puro (Bloque 18) no debe verse afectado por el nuevo
	parámetro opcional que usa el canal de WhatsApp para adjuntos."""

	def test_attachment_field_is_optional_and_defaults_to_none(self) -> None:
		source = (APP_ROOT / "conversation/dispatch.py").read_text(encoding="utf-8")
		self.assertIn('data.get("attachment_file_url")', source)

	def test_registry_still_has_exactly_seven_intents_unaffected_by_the_channel(self) -> None:
		import sys

		sys.path.insert(0, str(APP_ROOT))
		from nexora.conversation.registry import REGISTRY

		self.assertEqual(7, len(REGISTRY))


class TestDeactivateCredential(unittest.TestCase):
	"""Brecha real encontrada en la auditoría de experiencia: la pantalla podía
	conectar, probar y vincular, pero nunca pausar un canal ya activo sin
	borrar la credencial guardada — el propietario no tenía forma real de
	"Desactivar WhatsApp" desde NEXORA."""

	def source(self) -> str:
		return (APP_ROOT / "conversation/channels/whatsapp.py").read_text(encoding="utf-8")

	def test_deactivate_credential_is_whitelisted_and_gated_like_its_siblings(self) -> None:
		source = self.source()
		self.assertIn('@frappe.whitelist(methods=["POST"])\ndef deactivate_credential(', source)

	def test_deactivate_credential_never_deletes_the_stored_credential(self) -> None:
		"""Pausa, no borra — la credencial real (App ID/App Secret/token) sigue
		guardada para poder reactivar sin pedirla de nuevo al propietario."""
		body = function_body(self.source(), "deactivate_credential")
		self.assertNotIn(".delete(", body)
		self.assertNotIn("frappe.delete_doc(", body)
		self.assertIn('doc.status = "Inactive"', body)

	def test_deactivate_credential_refuses_to_deactivate_an_already_inactive_channel(self) -> None:
		body = function_body(self.source(), "deactivate_credential")
		self.assertIn('doc.status != "Active"', body)
		self.assertIn("frappe.throw(", body)

	def test_deactivate_credential_refuses_when_no_credential_exists(self) -> None:
		body = function_body(self.source(), "deactivate_credential")
		self.assertIn("if not doc:", body)


class TestConversationChannelsPageHasADeactivateAction(unittest.TestCase):
	def test_deactivate_button_is_wired_to_the_real_service(self) -> None:
		source = (
			APP_ROOT / "nexora/page/nexora_conversation_channels/nexora_conversation_channels.js"
		).read_text(encoding="utf-8")
		self.assertIn("Desactivar WhatsApp", source)
		self.assertIn("nexora.conversation.channels.whatsapp.deactivate_credential", source)

	def test_deactivate_button_asks_for_confirmation_first(self) -> None:
		"""Pausar un canal en producción no debe dispararse con un solo clic
		accidental — mismo estándar que ya exige confirmación para revocar un
		número vinculado en el resto de la pantalla."""
		source = (
			APP_ROOT / "nexora/page/nexora_conversation_channels/nexora_conversation_channels.js"
		).read_text(encoding="utf-8")
		body = source[source.index("async function deactivateCredential") :]
		self.assertIn("frappe.confirm(", body[:400])

	def test_credential_and_account_status_are_translated(self) -> None:
		"""Hallazgo real de auditoría visual (captura real del recorrido de CI,
		desktop-chromium-whatsapp-admin.png): la pantalla mostraba "Inactive"
		en inglés crudo junto a etiquetas en español ("Estado", "Número"...).
		`status` (`NXR Channel Credential`/`NXR Channel Account`) usa el mismo
		registro de traducciones que el resto de la aplicación
		(window.nexora.ui.label), no un valor sin traducir."""
		source = (
			APP_ROOT / "nexora/page/nexora_conversation_channels/nexora_conversation_channels.js"
		).read_text(encoding="utf-8")
		self.assertIn('escape(window.nexora.ui.label("status", status.status))', source)
		self.assertIn('escape(window.nexora.ui.label("status", row.status))', source)

		registry = (APP_ROOT / "public/js/nexora_report_actions.js").read_text(encoding="utf-8")
		status_block = registry.split("status: Object.freeze({", 1)[1].split("}),", 1)[0]
		# Conjunto real: NXR Channel Credential usa Active/Inactive, NXR Channel
		# Account usa Active/Revoked (ambos doctype.json, opciones del campo status).
		for value in ("Active", "Inactive", "Revoked"):
			with self.subTest(status=value):
				self.assertIn(f"{value}:", status_block)


if __name__ == "__main__":
	unittest.main()
