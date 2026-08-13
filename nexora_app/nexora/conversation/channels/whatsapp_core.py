"""Lógica pura del canal WhatsApp Business Cloud API (Bloque 21, NXR-INT-0008).

Sin dependencia de Frappe (mismo principio que ``purchases/request_core.py``/
``conversation/core.py``): verificación de firma HMAC-SHA256 y extracción de
mensajes reales del payload que Meta documenta. La resolución de credenciales,
el punto whitelisted del webhook y el envío por la Graph API viven en
``whatsapp.py`` (ese sí depende de Frappe). Nada aquí inventa un campo que
Meta no envíe — un mensaje sin forma reconocida se ignora, nunca se rellena
con un valor supuesto.
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping
from typing import Any

_MEDIA_TYPES = ("image", "document", "audio", "video")


def verify_signature(app_secret: str, body: bytes, signature_header: str | None) -> bool:
	"""Verifica ``X-Hub-Signature-256`` (HMAC-SHA256 del cuerpo crudo con el App
	Secret) — debe calcularse sobre los bytes exactos recibidos, antes de
	cualquier parseo JSON; un solo espacio de diferencia invalida la firma real
	que Meta calculó. Usa ``hmac.compare_digest`` para evitar una fuga por
	temporización en la comparación."""

	if not signature_header or not signature_header.startswith("sha256="):
		return False
	provided = signature_header[len("sha256=") :].strip()
	if not provided:
		return False
	expected = hmac.new(app_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
	return hmac.compare_digest(expected, provided)


def extract_verification_challenge(query: Mapping[str, Any], expected_verify_token: str) -> str | None:
	"""Responde a la verificación GET de Meta: devuelve ``hub.challenge`` solo si
	``hub.mode == "subscribe"`` y ``hub.verify_token`` coincide exactamente con
	el valor configurado — nunca se echa de vuelta un challenge sin validar el
	token, así sea el único parámetro presente."""

	mode = str(query.get("hub.mode") or "")
	token = str(query.get("hub.verify_token") or "")
	if mode != "subscribe":
		return None
	if not expected_verify_token or not hmac.compare_digest(token, expected_verify_token):
		return None
	challenge = query.get("hub.challenge")
	return str(challenge) if challenge is not None else None


def extract_inbound_messages(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
	"""Extrae los mensajes reales de un payload de webhook de WhatsApp Business
	Cloud API, ignorando eventos que no son mensajes entrantes (p. ej.
	actualizaciones de estado de entrega/lectura, que llegan en
	``value.statuses``, no en ``value.messages``).

	Forma real documentada por Meta:
	``{"entry": [{"changes": [{"value": {"messages": [...], "contacts": [...]}}]}]}``
	"""

	messages: list[dict[str, Any]] = []
	for entry in payload.get("entry") or []:
		for change in entry.get("changes") or []:
			value = change.get("value") or {}
			for message in value.get("messages") or []:
				normalized = _normalize_message(message)
				if normalized:
					messages.append(normalized)
	return messages


_KNOWN_STATUSES = ("sent", "delivered", "read", "failed")


def extract_status_updates(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
	"""Extrae actualizaciones reales de estado de entrega/lectura de un mensaje
	saliente (``value.statuses``) — la misma forma que ``extract_inbound_messages``
	ya reconocía y descartaba explícitamente, sin persistir nunca ningún estado.

	Forma real documentada por Meta:
	``{"entry": [{"changes": [{"value": {"statuses": [{"id": ..., "status": ...}]}}]}]}``
	"""

	updates: list[dict[str, Any]] = []
	for entry in payload.get("entry") or []:
		for change in entry.get("changes") or []:
			value = change.get("value") or {}
			for status in value.get("statuses") or []:
				normalized = _normalize_status(status)
				if normalized:
					updates.append(normalized)
	return updates


def _normalize_status(status: Mapping[str, Any]) -> dict[str, Any] | None:
	message_id = str(status.get("id") or "").strip()
	state = str(status.get("status") or "").strip().lower()
	if not message_id or state not in _KNOWN_STATUSES:
		return None
	error_detail = None
	if state == "failed":
		errors = status.get("errors") or []
		first = errors[0] if errors else {}
		error_detail = str((first or {}).get("title") or (first or {}).get("message") or "").strip() or None
	return {
		"message_id": message_id,
		"status": state,
		"timestamp": status.get("timestamp"),
		"error_detail": error_detail,
	}


def _normalize_message(message: Mapping[str, Any]) -> dict[str, Any] | None:
	message_id = str(message.get("id") or "").strip()
	sender = str(message.get("from") or "").strip()
	message_type = str(message.get("type") or "").strip()
	if not message_id or not sender or not message_type:
		return None
	normalized: dict[str, Any] = {
		"message_id": message_id,
		"from": sender,
		"type": message_type,
		"timestamp": message.get("timestamp"),
		"text": None,
		"media_id": None,
		"caption": None,
	}
	if message_type == "text":
		normalized["text"] = str((message.get("text") or {}).get("body") or "").strip() or None
	elif message_type in _MEDIA_TYPES:
		media = message.get(message_type) or {}
		normalized["media_id"] = str(media.get("id") or "").strip() or None
		normalized["caption"] = str(media.get("caption") or "").strip() or None
	else:
		# Tipo real de Meta que este canal todavía no interpreta (p. ej.
		# ubicación, contacto, interactivo) — se reconoce, no se descarta en
		# silencio, pero tampoco se inventa contenido de texto para él.
		pass
	return normalized
