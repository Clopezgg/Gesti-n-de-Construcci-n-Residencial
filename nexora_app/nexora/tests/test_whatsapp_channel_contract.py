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
		self.assertEqual(1, len(re.findall(r"^@frappe\.whitelist\(allow_guest=True", source, flags=re.MULTILINE)))
		self.assertIn(
			'@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])  # nosemgrep\ndef webhook()', source
		)

	def test_post_branch_verifies_the_signature_before_parsing_the_body(self) -> None:
		source = self.source()
		body = function_body(source, "webhook")
		verify_at = body.index("verify_signature(")
		parse_at = body.index("frappe.parse_json(")
		self.assertLess(verify_at, parse_at, "la firma debe verificarse antes de confiar en el payload")

	def test_webhook_never_trusts_a_client_supplied_verify_token_without_comparing_the_stored_one(self) -> None:
		source = self.source()
		body = function_body(source, "webhook")
		self.assertIn("extract_verification_challenge(frappe.local.form_dict, credential[\"verify_token\"])", body)

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
		self.assertEqual(4, source.count('.get_password('))
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


class TestPermissionActionsAreAdministratorOnly(unittest.TestCase):
	def test_manage_actions_map_to_administrator_only_roles(self) -> None:
		source = (APP_ROOT / "permissions.py").read_text(encoding="utf-8")
		block = source[source.index("ACTION_ROLES") : source.index("ACTION_ROLES") + source[source.index("ACTION_ROLES") :].index("\n}")]
		self.assertIn('"manage_channel_credential": ADMINISTRATOR_ONLY_ROLES', block)
		self.assertIn('"manage_channel_account": ADMINISTRATOR_ONLY_ROLES', block)

	def test_every_whitelisted_write_function_requires_an_action(self) -> None:
		source = (APP_ROOT / "conversation/channels/whatsapp.py").read_text(encoding="utf-8")
		for name in ("connect_credential", "test_channel_connection", "link_channel_account", "revoke_channel_account"):
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

	def test_page_restricted_to_administrative_roles_not_project_viewer(self) -> None:
		payload = json.loads(
			(APP_ROOT / "nexora/page/nexora_conversation_channels/nexora_conversation_channels.json").read_text(
				encoding="utf-8"
			)
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


if __name__ == "__main__":
	unittest.main()
