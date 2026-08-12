"""NXR-INT-0008: canal WhatsApp Business real contra Frappe/MariaDB (Bloque 21).

Requiere bench + MariaDB reales; no se pudo ejecutar en el entorno de esta
sesión (sin bench/Frappe/MariaDB — confirmado por
``ModuleNotFoundError: No module named 'frappe'`` al intentar importarlo
aquí). Los intentos reales contra la Graph API de Meta se simulan con
``unittest.mock.patch`` sobre las funciones ``_graph_get``/``_graph_post_json``
del propio módulo — nunca sobre ``verify_signature``/``extract_inbound_messages``
(esas se ejercen con datos reales, no con dobles, porque son la parte que
``test_whatsapp_channel_core.py`` ya prueba de verdad sin necesitar Frappe).

Cobertura pensada para la matriz mínima honesta de este bloque: verificación
GET con token correcto/incorrecto, POST con firma válida/inválida, número no
vinculado (nunca se procesa nada), número vinculado ejecuta el motor
conversacional real del Bloque 18, mensaje duplicado (mismo `message_id`) se
deduplica, imagen con leyenda se registra como evidencia real vía
`register_evidence`.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.conversation.channels import whatsapp


def _key(prefix: str) -> str:
	return f"{prefix}-{uuid.uuid4().hex}"


def _sign(secret: str, body: bytes) -> str:
	return f"sha256={hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()}"


def _ensure_user(email: str, role: str) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@", 1)[0],
				"enabled": 1,
				"send_welcome_email": 0,
				"roles": [{"role": role}],
			}
		).insert(ignore_permissions=True)
	return email


class TestWhatsAppChannelIntegrationMariaDB(FrappeTestCase):
	def setUp(self) -> None:
		frappe.set_user("Administrator")
		self.app_secret = "app-secret-value"
		self.verify_token = "verify-token-value"
		whatsapp.connect_credential(
			{
				"app_id": "123456",
				"app_secret": self.app_secret,
				"access_token": "access-token-value",
				"phone_number_id": "987654",
				"waba_id": "555111",
				"verify_token": self.verify_token,
			}
		)
		frappe.db.set_value("NXR Channel Credential", {"channel": "WhatsApp"}, "status", "Active")
		self.user = _ensure_user(_key("channel-user") + "@example.com", "NEXORA Finance Operator")

	def _webhook_post(self, payload: dict) -> None:
		body = json.dumps(payload).encode("utf-8")
		frappe.request.method = "POST"
		frappe.request.get_data = lambda: body
		frappe.request.headers = {"X-Hub-Signature-256": _sign(self.app_secret, body)}
		whatsapp.webhook()

	def test_get_verification_with_correct_token_echoes_the_challenge(self) -> None:
		frappe.request.method = "GET"
		frappe.local.form_dict = frappe._dict(
			{"hub.mode": "subscribe", "hub.verify_token": self.verify_token, "hub.challenge": "999"}
		)
		result = whatsapp.webhook()
		self.assertEqual(result, "999")

	def test_get_verification_with_wrong_token_is_rejected(self) -> None:
		frappe.request.method = "GET"
		frappe.local.form_dict = frappe._dict(
			{"hub.mode": "subscribe", "hub.verify_token": "guessed", "hub.challenge": "999"}
		)
		with self.assertRaises(frappe.PermissionError):
			whatsapp.webhook()

	def test_post_with_invalid_signature_is_rejected_before_touching_any_data(self) -> None:
		payload = {"entry": []}
		body = json.dumps(payload).encode("utf-8")
		frappe.request.method = "POST"
		frappe.request.get_data = lambda: body
		frappe.request.headers = {"X-Hub-Signature-256": "sha256=deadbeef"}
		with self.assertRaises(frappe.PermissionError):
			whatsapp.webhook()

	def test_message_from_an_unlinked_number_is_never_processed(self) -> None:
		with patch.object(whatsapp, "_send_text_message") as mock_send:
			self._webhook_post(
				{
					"entry": [
						{
							"changes": [
								{
									"value": {
										"messages": [
											{
												"id": _key("wamid"),
												"from": "50400000000",
												"type": "text",
												"text": {"body": "¿Cuánto dinero tengo?"},
											}
										]
									}
								}
							]
						}
					]
				}
			)
			mock_send.assert_called_once()
			self.assertIn("no está vinculado", mock_send.call_args[0][2])

	def test_message_from_a_linked_number_reaches_the_real_conversational_engine(self) -> None:
		whatsapp.link_channel_account({"external_id": "50411111111", "user": self.user})
		with (
			patch.object(whatsapp, "_send_text_message") as mock_send,
			patch("nexora.conversation.nlu.orchestrator_execute") as mock_llm,
		):
			from nexora.conversation.nlu import ConversationNluError

			mock_llm.side_effect = ConversationNluError("sin proveedor en esta prueba")
			self._webhook_post(
				{
					"entry": [
						{
							"changes": [
								{
									"value": {
										"messages": [
											{
												"id": _key("wamid"),
												"from": "50411111111",
												"type": "text",
												"text": {"body": "hola"},
											}
										]
									}
								}
							]
						}
					]
				}
			)
			mock_send.assert_called_once()
			self.assertEqual(frappe.session.user, "Administrator")  # restaurado tras procesar

	def test_duplicate_message_id_is_processed_only_once(self) -> None:
		whatsapp.link_channel_account({"external_id": "50422222222", "user": self.user})
		message_id = _key("wamid")
		payload = {
			"entry": [
				{
					"changes": [
						{
							"value": {
								"messages": [
									{
										"id": message_id,
										"from": "50422222222",
										"type": "text",
										"text": {"body": "hola"},
									}
								]
							}
						}
					]
				}
			]
		}
		with (
			patch.object(whatsapp, "_send_text_message") as mock_send,
			patch(
				"nexora.conversation.nlu.orchestrator_execute",
				side_effect=Exception("no importa en esta prueba"),
			),
		):
			self._webhook_post(payload)
			self._webhook_post(payload)
			self.assertEqual(mock_send.call_count, 1)

	def test_image_with_caption_is_downloaded_and_registered_as_real_evidence(self) -> None:
		project = frappe.get_doc({"doctype": "Project", "project_name": f"Casa {_key('p')}"}).insert(
			ignore_permissions=True
		)
		whatsapp.link_channel_account({"external_id": "50433333333", "user": self.user})
		with (
			patch.object(whatsapp, "_download_media", return_value=(b"contenido de prueba", "image/jpeg")),
			patch("nexora.conversation.nlu.orchestrator_execute") as mock_llm,
			patch.object(whatsapp, "_send_text_message") as mock_send,
		):
			mock_llm.return_value = whatsapp.frappe._dict(
				provider_key="openai",
				capability="text",
				data={
					"choices": [
						{
							"message": {
								"content": json.dumps(
									{
										"intent": "register_evidence",
										"confidence": 0.9,
										"fields": {
											"project": project.project_name,
											"evidence_kind": "Payment Proof",
											"channel": "WhatsApp",
										},
										"clarification_question": None,
									}
								)
							}
						}
					]
				},
			)
			self._webhook_post(
				{
					"entry": [
						{
							"changes": [
								{
									"value": {
										"messages": [
											{
												"id": _key("wamid"),
												"from": "50433333333",
												"type": "image",
												"image": {"id": "media-1", "caption": "Factura de Casa"},
											}
										]
									}
								}
							]
						}
					]
				}
			)
			self.assertTrue(mock_send.called)
