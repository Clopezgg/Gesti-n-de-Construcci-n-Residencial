"""Canal WhatsApp Business Cloud API real (Bloque 21, NXR-INT-0008).

Reutiliza el motor conversacional ya construido (Bloque 18,
``conversation.dispatch``) — este módulo solo traduce entre el formato de
Meta y el mensaje canónico `{"text": ...}` que ``dispatch.send_message`` ya
entiende. Nunca decide una intención ni ejecuta una operación por su cuenta.

Patrón de credenciales idéntico al ya certificado en
``intelligence/credentials.py`` + ``intelligence/runtime.py``: nada se prueba
con datos falsos — probar la conexión significa una llamada HTTP real contra
la Graph API de Meta (mismo principio que corrigió NXR-INT-0007 en el
Bloque 15).

**Advertencia de implementación honesta:** este entorno no tiene Frappe
instalado, por lo que el mecanismo exacto para devolver texto plano (no
envuelto en JSON) desde una función ``@frappe.whitelist`` — necesario para el
reto de verificación GET de Meta — se implementó según la convención mejor
conocida de Frappe (``frappe.response["type"] = "text"``), pero **no se pudo
verificar contra una instancia real**. Si la verificación del webhook falla
en el primer intento real, revisar este punto exacto primero.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.conversation import db as conversation_db
from nexora.conversation import dispatch
from nexora.conversation.channels.whatsapp_core import (
	extract_inbound_messages,
	extract_verification_challenge,
	verify_signature,
)
from nexora.financial.context import service_write
from nexora.financial.core import canonical_payload_hash
from nexora.financial.db import correlation, parse_payload
from nexora.integrations.core import redact_credentials
from nexora.permissions import require_action

CREDENTIAL_DOCTYPE = "NXR Channel Credential"
ACCOUNT_DOCTYPE = "NXR Channel Account"
GRAPH_API_VERSION = "v19.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
_DEDUP_CACHE_PREFIX = "nexora:whatsapp:webhook_message:"
_DEDUP_TTL_SECONDS = 60 * 60 * 24


class WhatsAppChannelError(Exception):
	"""Error real de red/API contra la Graph API de Meta — nunca un valor inventado."""


def _redacted_fingerprint(data: Mapping[str, Any]) -> str:
	summary = " ".join(f"{key}={value}" for key, value in sorted(data.items()))
	return canonical_payload_hash({"redacted": redact_credentials(summary)})


def _credential_doc() -> Any | None:
	name = frappe.db.get_value(CREDENTIAL_DOCTYPE, {"channel": "WhatsApp"}, "name")
	return frappe.get_doc(CREDENTIAL_DOCTYPE, name) if name else None


def _active_credential() -> dict[str, Any] | None:
	"""Credencial activa con los secretos ya resueltos (nunca registrados ni
	impresos) — ``None`` si no hay ninguna o si está ``Inactive``."""

	doc = _credential_doc()
	if not doc or doc.status != "Active":
		return None
	return {
		"name": doc.name,
		"app_secret": doc.get_password("app_secret"),
		"access_token": doc.get_password("access_token"),
		"verify_token": doc.get_password("verify_token"),
		"phone_number_id": doc.phone_number_id,
		"waba_id": doc.waba_id,
	}


def _graph_get(path: str, access_token: str, *, timeout_seconds: int = 30) -> dict[str, Any]:
	request = urllib.request.Request(
		f"{GRAPH_API_BASE}/{path}",
		headers={"Authorization": f"Bearer {access_token}"},
		method="GET",
	)
	try:
		with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
			return json.loads(response.read().decode("utf-8") or "{}")
	except urllib.error.HTTPError as exc:
		detail = exc.read().decode("utf-8", errors="replace")[:300]
		raise WhatsAppChannelError(f"Meta respondió HTTP {exc.code} a la consulta: {detail}") from exc
	except urllib.error.URLError as exc:
		raise WhatsAppChannelError(f"No se pudo conectar con la Graph API de Meta: {exc.reason}") from exc


def _graph_post_json(path: str, access_token: str, payload: Mapping[str, Any], *, timeout_seconds: int = 30) -> dict[str, Any]:
	body = json.dumps(payload).encode("utf-8")
	request = urllib.request.Request(
		f"{GRAPH_API_BASE}/{path}",
		data=body,
		headers={
			"Authorization": f"Bearer {access_token}",
			"Content-Type": "application/json",
		},
		method="POST",
	)
	try:
		with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
			return json.loads(response.read().decode("utf-8") or "{}")
	except urllib.error.HTTPError as exc:
		detail = exc.read().decode("utf-8", errors="replace")[:300]
		raise WhatsAppChannelError(f"Meta respondió HTTP {exc.code} al enviar el mensaje: {detail}") from exc
	except urllib.error.URLError as exc:
		raise WhatsAppChannelError(f"No se pudo conectar con la Graph API de Meta: {exc.reason}") from exc


def _send_text_message(credential: Mapping[str, Any], to: str, body: str) -> dict[str, Any]:
	payload = {
		"messaging_product": "whatsapp",
		"to": to,
		"type": "text",
		"text": {"body": body[:4096]},
	}
	return _graph_post_json(f"{credential['phone_number_id']}/messages", credential["access_token"], payload)


def _download_media(credential: Mapping[str, Any], media_id: str) -> tuple[bytes, str]:
	"""Descarga real en dos pasos (documentado por Meta): resolver la URL
	firmada y de corta duración del medio, luego descargar su contenido — ambas
	solicitudes exigen el mismo token de acceso."""

	metadata = _graph_get(media_id, credential["access_token"])
	media_url = str(metadata.get("url") or "")
	if not media_url:
		raise WhatsAppChannelError("Meta no devolvió una URL de descarga para el medio.")
	request = urllib.request.Request(media_url, headers={"Authorization": f"Bearer {credential['access_token']}"})
	try:
		with urllib.request.urlopen(request, timeout=30) as response:
			return response.read(), str(metadata.get("mime_type") or "application/octet-stream")
	except urllib.error.HTTPError as exc:
		raise WhatsAppChannelError(f"Meta respondió HTTP {exc.code} al descargar el medio.") from exc
	except urllib.error.URLError as exc:
		raise WhatsAppChannelError(f"No se pudo descargar el medio: {exc.reason}") from exc


def _already_processed(message_id: str) -> bool:
	"""Meta puede reintentar la entrega del mismo webhook — deduplicar por
	``message_id`` real con una marca de corta vida, sin necesidad de un nuevo
	campo de esquema para un identificador que solo importa 24 horas."""

	cache = frappe.cache()
	key = f"{_DEDUP_CACHE_PREFIX}{message_id}"
	return bool(cache.get_value(key))


def _mark_processed(message_id: str) -> None:
	cache = frappe.cache()
	key = f"{_DEDUP_CACHE_PREFIX}{message_id}"
	cache.set_value(key, "1", expires_in_sec=_DEDUP_TTL_SECONDS)


def _resolve_channel_account(external_id: str) -> str | None:
	return frappe.db.get_value(
		ACCOUNT_DOCTYPE, {"channel": "WhatsApp", "external_id": external_id, "status": "Active"}, "user"
	)


def _process_message(credential: Mapping[str, Any], message: Mapping[str, Any]) -> None:
	if _already_processed(message["message_id"]):
		return
	sender = message["from"]
	user = _resolve_channel_account(sender)
	if not user:
		_send_text_message(
			credential,
			sender,
			_(
				"Este número no está vinculado a ninguna cuenta de NEXORA. Pide a un "
				"administrador que lo conecte desde el panel de canales."
			),
		)
		_mark_processed(message["message_id"])
		return

	text = message.get("text")
	attachment_file_url = None
	if message.get("media_id"):
		try:
			content, mime_type = _download_media(credential, message["media_id"])
		except WhatsAppChannelError:
			_send_text_message(credential, sender, _("No pude descargar el archivo adjunto. Intenta enviarlo de nuevo."))
			_mark_processed(message["message_id"])
			return
		extension = mime_type.split("/")[-1].split(";")[0] or "bin"
		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"whatsapp-{message['message_id']}.{extension}",
				"is_private": 1,
				"content": content,
			}
		).insert(ignore_permissions=True)
		attachment_file_url = file_doc.file_url
		text = message.get("caption") or "Guarda esta evidencia."

	if not text:
		_send_text_message(credential, sender, _("No pude leer el contenido de tu mensaje."))
		_mark_processed(message["message_id"])
		return

	previous_user = frappe.session.user
	try:
		frappe.set_user(user)
		result = dispatch.send_message({"text": text, "attachment_file_url": attachment_file_url})
	finally:
		frappe.set_user(previous_user)
	reply = str(result.get("message") or "")
	if reply:
		_send_text_message(credential, sender, reply)
	_mark_processed(message["message_id"])


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def webhook() -> Any:
	credential = _active_credential()
	if frappe.request.method == "GET":
		if not credential:
			frappe.throw(_("Canal de WhatsApp no configurado."), frappe.PermissionError)
		challenge = extract_verification_challenge(frappe.local.form_dict, credential["verify_token"])
		if challenge is None:
			frappe.throw(_("Verificación de webhook rechazada."), frappe.PermissionError)
		frappe.response["type"] = "text"
		return challenge

	if not credential:
		frappe.throw(_("Canal de WhatsApp no configurado."), frappe.PermissionError)
	raw_body = frappe.request.get_data()
	signature = frappe.request.headers.get("X-Hub-Signature-256")
	if not verify_signature(credential["app_secret"], raw_body, signature):
		frappe.throw(_("Firma de webhook inválida."), frappe.PermissionError)
	payload = frappe.parse_json(raw_body.decode("utf-8") or "{}")
	for message in extract_inbound_messages(payload):
		_process_message(credential, message)
	return {"status": "ok"}


@frappe.whitelist(methods=["POST"])
def connect_credential(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Guarda o reemplaza la credencial de WhatsApp — nunca la prueba contra
	Meta aquí (eso es ``test_channel_connection``, una acción explícita y
	separada, mismo principio que ``intelligence.service.save_credential`` vs.
	``test_provider_connection``)."""

	data = parse_payload(payload)
	require_action("manage_channel_credential")
	required_fields = ("app_id", "app_secret", "access_token", "phone_number_id", "waba_id", "verify_token")
	missing = [field for field in required_fields if not str(data.get(field) or "").strip()]
	if missing:
		frappe.throw(_("Faltan campos obligatorios: {0}.").format(", ".join(missing)))

	fingerprint = _redacted_fingerprint({key: "***" for key in required_fields})
	correlation_id = correlation(data)
	doc = _credential_doc()
	with service_write():
		if doc:
			for field in required_fields:
				doc.set(field, data[field])
			doc.status = "Inactive"
			doc.payload_hash = fingerprint
			doc.correlation_id = correlation_id
			doc.save(ignore_permissions=True)
		else:
			doc = frappe.get_doc(
				{
					"doctype": CREDENTIAL_DOCTYPE,
					"channel": "WhatsApp",
					"status": "Inactive",
					**{field: data[field] for field in required_fields},
					"connected_by": frappe.session.user,
					"connected_at": frappe.utils.now_datetime(),
					"payload_hash": fingerprint,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
	return {"credential": doc.name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def test_channel_connection(payload: str | Mapping[str, Any] | None = None) -> dict[str, Any]:
	"""Prueba real (NXR-INT-0007 aplicado aquí también): consulta el propio
	número contra la Graph API con el token guardado. Si Meta lo confirma,
	activa el canal; si lo rechaza, lo deja ``Inactive`` con el detalle real
	del rechazo — nunca ``"Success"`` sin haber llamado a nadie."""

	require_action("manage_channel_credential")
	doc = _credential_doc()
	if not doc:
		frappe.throw(_("No hay ninguna credencial de WhatsApp guardada."))
	access_token = doc.get_password("access_token")
	try:
		response = _graph_get(
			f"{doc.phone_number_id}?fields=display_phone_number,verified_name", access_token
		)
	except WhatsAppChannelError as exc:
		with service_write():
			doc.status = "Inactive"
			doc.last_test_at = frappe.utils.now_datetime()
			doc.last_test_result = str(exc)
			doc.save(ignore_permissions=True)
		return {"success": False, "detail": str(exc)}

	with service_write():
		doc.status = "Active"
		doc.display_phone_number = response.get("display_phone_number") or doc.display_phone_number
		doc.last_test_at = frappe.utils.now_datetime()
		doc.last_test_result = "Success"
		doc.save(ignore_permissions=True)
	return {
		"success": True,
		"display_phone_number": response.get("display_phone_number"),
		"verified_name": response.get("verified_name"),
	}


@frappe.whitelist(methods=["POST"])
def link_channel_account(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("manage_channel_account")
	external_id = str(data.get("external_id") or "").strip()
	user = str(data.get("user") or "").strip()
	if not external_id or not user:
		frappe.throw(_("Indique el número (formato wa_id) y el usuario a vincular."))
	if not frappe.db.exists("User", user):
		frappe.throw(_("El usuario indicado no existe."))
	with service_write():
		doc = frappe.get_doc(
			{
				"doctype": ACCOUNT_DOCTYPE,
				"channel": "WhatsApp",
				"external_id": external_id,
				"user": user,
				"status": "Active",
				"linked_by": frappe.session.user,
				"linked_at": frappe.utils.now_datetime(),
				"correlation_id": correlation(data),
			}
		).insert(ignore_permissions=True)
	return {"channel_account": doc.name, "external_id": external_id, "user": user}


@frappe.whitelist(methods=["POST"])
def revoke_channel_account(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("manage_channel_account")
	name = str(data.get("channel_account") or "").strip()
	if not name:
		frappe.throw(_("Indique qué cuenta de canal revocar."))
	doc = frappe.get_doc(ACCOUNT_DOCTYPE, name)
	with service_write():
		doc.status = "Revoked"
		doc.revoked_by = frappe.session.user
		doc.revoked_at = frappe.utils.now_datetime()
		doc.save(ignore_permissions=True)
	return {"channel_account": doc.name, "status": "Revoked"}


@frappe.whitelist(methods=["POST"])
def list_channel_accounts(payload: str | Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
	require_action("view_channel")
	rows = frappe.get_all(
		ACCOUNT_DOCTYPE,
		filters={"channel": "WhatsApp"},
		fields=["name", "external_id", "user", "status", "linked_at"],
		order_by="modified desc",
	)
	return list(rows)


@frappe.whitelist(methods=["POST"])
def get_channel_status(payload: str | Mapping[str, Any] | None = None) -> dict[str, Any]:
	require_action("view_channel")
	doc = _credential_doc()
	if not doc:
		return {"configured": False}
	return {
		"configured": True,
		"status": doc.status,
		"display_phone_number": doc.display_phone_number,
		"last_test_at": doc.last_test_at,
		"last_test_result": doc.last_test_result,
	}
