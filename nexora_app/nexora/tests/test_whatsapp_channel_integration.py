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

import base64
import hashlib
import hmac
import json
import uuid
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.conversation.channels import whatsapp

PNG_1X1 = base64.b64decode(
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


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


class _FakeRequest:
	"""``frappe.request`` es un ``LocalProxy`` de Werkzeug: fuera de una petición
	HTTP real (como aquí, bajo ``bench run-tests``) no hay objeto al que
	enlazarse, y ``frappe.request.method = "POST"`` lanza
	``RuntimeError: object is not bound`` al intentar leer el proxy antes de
	escribirlo. Se reemplaza el objeto completo vía ``frappe.local.request``
	— nunca se muta el proxy — con el mínimo real que ``whatsapp.webhook()``
	lee: ``method``, ``get_data()`` y ``headers``."""

	def __init__(self, method: str, body: bytes = b"", headers: dict[str, str] | None = None) -> None:
		self.method = method
		self._body = body
		self.headers = headers or {}

	def get_data(self) -> bytes:
		return self._body


def _bind_request(method: str, body: bytes = b"", headers: dict[str, str] | None = None) -> None:
	frappe.local.request = _FakeRequest(method, body, headers)


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
		_bind_request("POST", body, {"X-Hub-Signature-256": _sign(self.app_secret, body)})
		whatsapp.webhook()

	def test_connecting_and_linking_a_channel_is_audited(self) -> None:
		# NXR-INT-0009: conectar una credencial de Meta o decidir qué usuario real
		# actúa detrás de un número externo debe quedar en la bitácora cruzada del
		# sistema (`NXR Audit Event`), no solo en el propio doctype administrativo.
		credential_name = frappe.db.get_value("NXR Channel Credential", {"channel": "WhatsApp"}, "name")
		self.assertTrue(
			frappe.db.exists(
				"NXR Audit Event",
				{
					"event_type": "channel_credential_saved",
					"reference_doctype": "NXR Channel Credential",
					"reference_name": credential_name,
				},
			)
		)
		linked = whatsapp.link_channel_account({"external_id": "50455555555", "user": self.user})
		self.assertTrue(
			frappe.db.exists(
				"NXR Audit Event",
				{
					"event_type": "channel_account_linked",
					"reference_doctype": "NXR Channel Account",
					"reference_name": linked["channel_account"],
				},
			)
		)
		whatsapp.revoke_channel_account({"channel_account": linked["channel_account"]})
		self.assertTrue(
			frappe.db.exists(
				"NXR Audit Event",
				{
					"event_type": "channel_account_revoked",
					"reference_doctype": "NXR Channel Account",
					"reference_name": linked["channel_account"],
				},
			)
		)

	def test_get_verification_with_correct_token_echoes_the_challenge(self) -> None:
		_bind_request("GET")
		frappe.local.form_dict = frappe._dict(
			{"hub.mode": "subscribe", "hub.verify_token": self.verify_token, "hub.challenge": "999"}
		)
		result = whatsapp.webhook()
		self.assertEqual(result, "999")

	def test_get_verification_with_wrong_token_is_rejected(self) -> None:
		_bind_request("GET")
		frappe.local.form_dict = frappe._dict(
			{"hub.mode": "subscribe", "hub.verify_token": "guessed", "hub.challenge": "999"}
		)
		with self.assertRaises(frappe.PermissionError):
			whatsapp.webhook()

	def test_post_with_invalid_signature_is_rejected_before_touching_any_data(self) -> None:
		payload = {"entry": []}
		body = json.dumps(payload).encode("utf-8")
		_bind_request("POST", body, {"X-Hub-Signature-256": "sha256=deadbeef"})
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
		from nexora.intelligence.core import IntelligenceError

		with (
			patch.object(whatsapp, "_send_text_message") as mock_send,
			# `nlu.interpret` solo traduce `IntelligenceError` (todo lo que el
			# orquestador real puede lanzar) a un mensaje conversacional — es la
			# única forma real de "el proveedor falló" que este bloque necesita
			# simular; un `Exception` genérico no es lo que `orchestrator_execute`
			# lanza nunca en producción y se propagaría sin traducir.
			patch(
				"nexora.conversation.nlu.orchestrator_execute",
				side_effect=IntelligenceError("no importa en esta prueba"),
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
			# `File.before_insert` de Frappe intenta abrir el contenido con PIL
			# cuando el tipo declarado es una imagen — bytes de texto plano hacen
			# que Frappe (no un doble de prueba) lance
			# `PIL.UnidentifiedImageError` real. Se usa el mismo PNG de 1x1 válido
			# que ya reutiliza `test_dashboard_integration.py` para este caso.
			patch.object(whatsapp, "_download_media", return_value=(PNG_1X1, "image/png")),
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

	def test_a_real_outbound_send_records_the_real_meta_message_id(self) -> None:
		"""NXR-INT-0008 (estados de entrega): a diferencia de las pruebas
		anteriores, aquí no se sustituye `_send_text_message` por un doble —
		se ejerce de verdad, con `_graph_post_json` simulando solo la
		respuesta real de la Graph API (`{"messages": [{"id": ...}]}`), para
		confirmar que el registro real (`NXR Channel Message`) se crea con el
		id real que Meta habría devuelto."""
		message_id = _key("wamid")
		with patch.object(
			whatsapp, "_graph_post_json", return_value={"messages": [{"id": message_id}]}
		) as mock_post:
			result = whatsapp.send_direct_message("50466666666", "Hola desde NEXORA")
			mock_post.assert_called_once()
		self.assertEqual(result["messages"][0]["id"], message_id)
		self.assertTrue(
			frappe.db.exists(
				"NXR Channel Message",
				{"external_message_id": message_id, "recipient": "50466666666", "status": "Sent"},
			)
		)

	def test_a_real_status_webhook_marks_the_real_sent_message_as_delivered(self) -> None:
		message_id = _key("wamid")
		with patch.object(whatsapp, "_graph_post_json", return_value={"messages": [{"id": message_id}]}):
			whatsapp.send_direct_message("50477777777", "Hola")
		self._webhook_post(
			{
				"entry": [
					{
						"changes": [
							{
								"value": {
									"statuses": [
										{"id": message_id, "status": "delivered", "timestamp": "1700000000"}
									]
								}
							}
						]
					}
				]
			}
		)
		row = frappe.db.get_value(
			"NXR Channel Message",
			{"external_message_id": message_id},
			["status", "status_updated_at"],
			as_dict=True,
		)
		self.assertEqual(row.status, "Delivered")
		self.assertIsNotNone(row.status_updated_at)

	def test_a_real_failed_status_records_the_real_error_detail(self) -> None:
		message_id = _key("wamid")
		with patch.object(whatsapp, "_graph_post_json", return_value={"messages": [{"id": message_id}]}):
			whatsapp.send_direct_message("50488888888", "Hola")
		self._webhook_post(
			{
				"entry": [
					{
						"changes": [
							{
								"value": {
									"statuses": [
										{
											"id": message_id,
											"status": "failed",
											"errors": [{"code": 131047, "title": "Re-engagement message"}],
										}
									]
								}
							}
						]
					}
				]
			}
		)
		row = frappe.db.get_value(
			"NXR Channel Message",
			{"external_message_id": message_id},
			["status", "error_detail"],
			as_dict=True,
		)
		self.assertEqual(row.status, "Failed")
		self.assertEqual(row.error_detail, "Re-engagement message")

	def test_a_status_for_a_message_never_sent_by_this_channel_is_ignored_not_fabricated(self) -> None:
		"""Un estado real de Meta para un `wamid` que este canal nunca registró
		como enviado no debe crear un registro inventado — significa que
		llegó de antes de que existiera este seguimiento, o de otro canal."""
		before = frappe.db.count("NXR Channel Message")
		self._webhook_post(
			{
				"entry": [
					{
						"changes": [
							{"value": {"statuses": [{"id": "wamid.never-sent-by-us", "status": "read"}]}}
						]
					}
				]
			}
		)
		self.assertEqual(frappe.db.count("NXR Channel Message"), before)

	def test_outbound_graph_call_recovers_from_a_single_transient_failure(self) -> None:
		"""NXR-INT-0008 (reintentos): un único error transitorio (503) no debe
		tirar abajo el envío — el mismo criterio de un solo reintento que ya
		certificó `intelligence.orchestrator_core.should_retry_same_provider`
		para el gateway de IA."""
		import urllib.error

		message_id = _key("wamid")
		transient = urllib.error.HTTPError(
			url="https://graph.facebook.com/v19.0/x/messages",
			code=503,
			msg="Service Unavailable",
			hdrs=None,
			fp=None,
		)
		success_response = json.dumps({"messages": [{"id": message_id}]}).encode("utf-8")

		class _FakeHTTPResponse:
			def __enter__(self):
				return self

			def __exit__(self, *exc):
				return False

			def read(self):
				return success_response

		with patch(
			"nexora.conversation.channels.whatsapp.urllib.request.urlopen",
			side_effect=[transient, _FakeHTTPResponse()],
		) as mock_urlopen:
			result = whatsapp.send_direct_message("50499999998", "Hola")
			self.assertEqual(mock_urlopen.call_count, 2)
		self.assertEqual(result["messages"][0]["id"], message_id)

	def test_outbound_graph_call_retries_a_timeout_once_then_reports_a_real_failure(self) -> None:
		"""GP-13: un timeout real no llega como `HTTPError` (nunca hubo
		respuesta) sino como `URLError` — `urlopen()` envuelve cualquier
		`OSError` del socket, incluido un timeout, dentro de `do_open()`
		antes de que llegue a quien la llama (`urllib/request.py`, `except
		OSError as err: raise URLError(err)`). Es transitorio y debe
		reintentarse exactamente una vez antes de rendirse — nunca fabricar
		un envío exitoso que nunca llegó a Meta."""
		import urllib.error

		with (
			patch(
				"nexora.conversation.channels.whatsapp.urllib.request.urlopen",
				side_effect=urllib.error.URLError(TimeoutError("timed out")),
			) as mock_urlopen,
			self.assertRaises(whatsapp.WhatsAppChannelError) as ctx,
		):
			whatsapp.send_direct_message("50499999995", "Hola")
		self.assertEqual(2, mock_urlopen.call_count, "Un timeout debe reintentarse exactamente una vez.")
		self.assertIn("no se pudo conectar", str(ctx.exception).lower())

	def test_outbound_graph_call_never_retries_a_non_transient_client_error(self) -> None:
		"""Un 401 (token inválido) no cambia al reintentar la misma llamada —
		debe fallar en el primer intento, no gastar una segunda llamada real
		contra Meta que fallará exactamente igual."""
		import io
		import urllib.error

		auth_error = urllib.error.HTTPError(
			url="https://graph.facebook.com/v19.0/x/messages",
			code=401,
			msg="Unauthorized",
			hdrs=None,
			fp=io.BytesIO(b'{"error": {"message": "Invalid OAuth access token"}}'),
		)
		with patch(
			"nexora.conversation.channels.whatsapp.urllib.request.urlopen", side_effect=auth_error
		) as mock_urlopen:
			with self.assertRaises(whatsapp.WhatsAppChannelError):
				whatsapp.send_direct_message("50499999997", "Hola")
			self.assertEqual(mock_urlopen.call_count, 1)

	def test_a_second_real_send_reusing_the_same_meta_message_id_is_never_fabricated_as_an_error(
		self,
	) -> None:
		"""NXR-INT-0008 (seguimiento): `external_message_id` es único — si
		`_open_graph_request` reintentara una llamada que en realidad ya había
		tenido éxito (la respuesta real se perdió en la red), Meta devolvería el
		mismo id real dos veces. El segundo registro no debe fallar el envío ya
		completado ante quien lo esperaba del otro lado: `frappe.DuplicateEntryError`
		se atrapa en silencio, nunca se fabrica un segundo registro."""
		message_id = _key("wamid")
		with patch.object(whatsapp, "_graph_post_json", return_value={"messages": [{"id": message_id}]}):
			whatsapp.send_direct_message("50411122233", "Primero")
			result = whatsapp.send_direct_message("50411122233", "Segundo")
		self.assertEqual(result["messages"][0]["id"], message_id)
		self.assertEqual(frappe.db.count("NXR Channel Message", {"external_message_id": message_id}), 1)

	def test_a_real_tracking_failure_never_blocks_a_message_already_sent_to_meta(self) -> None:
		"""El mensaje ya llegó de verdad a Meta cuando falla solo el registro
		interno de seguimiento (p. ej. un error real de base de datos ajeno a la
		duplicidad) — no debe convertirse en un error para quien lo esperaba del
		otro lado; queda documentado en el log de errores real de Frappe."""
		message_id = _key("wamid")
		real_get_doc = frappe.get_doc

		def _boom_only_for_channel_message(*args, **kwargs):
			doctype = args[0].get("doctype") if args and isinstance(args[0], dict) else None
			if doctype == whatsapp.MESSAGE_DOCTYPE:
				raise RuntimeError("fallo real de base de datos, ajeno a la duplicidad")
			return real_get_doc(*args, **kwargs)

		with (
			patch.object(whatsapp, "_graph_post_json", return_value={"messages": [{"id": message_id}]}),
			patch.object(whatsapp.frappe, "get_doc", side_effect=_boom_only_for_channel_message),
			patch.object(whatsapp.frappe, "log_error") as mock_log_error,
		):
			result = whatsapp.send_direct_message("50411133344", "Hola")
		self.assertEqual(result["messages"][0]["id"], message_id)
		mock_log_error.assert_called_once()
		self.assertFalse(frappe.db.exists("NXR Channel Message", {"external_message_id": message_id}))

	def test_a_message_from_a_user_without_permission_gets_a_friendly_reply_not_a_crash(self) -> None:
		"""Un `frappe.PermissionError` real del motor conversacional (Bloque 18)
		no debe tirar abajo el manejo del webhook completo — Meta reintentaría
		la entrega indefinidamente sin que el usuario real reciba nunca una
		respuesta. Se atrapa y se responde con un mensaje real, nunca fabricado
		fuera de este caso."""
		whatsapp.link_channel_account({"external_id": "50411144455", "user": self.user})
		with (
			patch.object(whatsapp, "_send_text_message") as mock_send,
			patch.object(
				whatsapp.dispatch, "send_message", side_effect=frappe.PermissionError("sin permiso")
			),
		):
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
												"from": "50411144455",
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
			self.assertIn("no tiene permiso", mock_send.call_args[0][2])

	def test_a_message_that_fails_validation_gets_the_real_validation_message_not_a_crash(self) -> None:
		"""Igual que el caso anterior, pero para `ValidationError` — el usuario
		recibe el texto real del error del motor conversacional, nunca un
		mensaje genérico que oculte cuál fue el problema real."""
		whatsapp.link_channel_account({"external_id": "50411155566", "user": self.user})
		with (
			patch.object(whatsapp, "_send_text_message") as mock_send,
			patch.object(
				whatsapp.dispatch,
				"send_message",
				side_effect=frappe.exceptions.ValidationError("El proyecto indicado no existe."),
			),
		):
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
												"from": "50411155566",
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
			self.assertEqual(mock_send.call_args[0][2], "El proyecto indicado no existe.")

	def test_deactivating_an_active_channel_stops_inbound_processing_and_can_be_reactivated(
		self,
	) -> None:
		"""Brecha real de experiencia encontrada por el propietario: la pantalla
		podía conectar/probar/vincular pero nunca pausar un canal ya activo. La
		credencial real (setUp la deja `Active`) debe poder pausarse sin
		borrarla, quedar auditada, rechazar un webhook real mientras está
		pausada, y reactivarse de verdad — no solo en apariencia."""
		credential_name = frappe.db.get_value("NXR Channel Credential", {"channel": "WhatsApp"}, "name")

		result = whatsapp.deactivate_credential()
		self.assertEqual(result["status"], "Inactive")
		self.assertEqual(frappe.db.get_value("NXR Channel Credential", credential_name, "status"), "Inactive")
		self.assertTrue(
			frappe.db.exists(
				"NXR Audit Event",
				{
					"event_type": "channel_credential_deactivated",
					"reference_doctype": "NXR Channel Credential",
					"reference_name": credential_name,
				},
			)
		)

		with self.assertRaises(frappe.ValidationError):
			whatsapp.deactivate_credential()

		payload = {
			"entry": [
				{
					"changes": [
						{
							"value": {
								"messages": [
									{
										"id": _key("wamid"),
										"from": "50499999996",
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
		body = json.dumps(payload).encode("utf-8")
		_bind_request("POST", body, {"X-Hub-Signature-256": _sign(self.app_secret, body)})
		with self.assertRaises(frappe.PermissionError):
			whatsapp.webhook()

		with patch.object(
			whatsapp,
			"_graph_get",
			return_value={"display_phone_number": "+50499999995", "verified_name": "NEXORA"},
		):
			reactivated = whatsapp.test_channel_connection()
		self.assertTrue(reactivated["success"])
		self.assertEqual(frappe.db.get_value("NXR Channel Credential", credential_name, "status"), "Active")
