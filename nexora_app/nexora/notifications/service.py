"""Notificaciones reales (Bloque 23, NXR-NOT-0006).

Distingue de verdad Creado/Entregado/Fallido — nunca convierte un registro
interno en evidencia de entrega. Inbox/PWA se marcan entregados al crearse
(la bandeja de la app/PWA instalada ES el mecanismo de entrega). Email usa
``frappe.sendmail`` real (mecanismo nativo de Frappe, no un mock); WhatsApp
reutiliza el canal real ya construido en el Bloque 21
(``conversation.channels.whatsapp.send_direct_message``). Ninguno de los dos
se marca "Delivered" sin que la llamada real correspondiente haya tenido
éxito.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.conversation.channels.whatsapp import (
	WhatsAppChannelError,
	resolve_external_id_for_user,
	send_direct_message,
)
from nexora.financial.context import service_write
from nexora.financial.core import canonical_payload_hash
from nexora.financial.db import audit, correlation, parse_payload
from nexora.notifications.core import (
	can_retry_delivery,
	requires_external_delivery,
	validate_channel,
	validate_priority,
)
from nexora.permissions import has_action, require_action


def _existing_by_idempotency_key(key: str) -> str | None:
	if not key:
		return None
	return frappe.db.get_value("NXR Notification", {"idempotency_key": key}, "name")


def _snapshot(doc: Any) -> dict[str, Any]:
	return {
		"notification": doc.name,
		"document_number": doc.document_number,
		"channel": doc.channel,
		"delivery_status": doc.delivery_status,
		"failure_reason": doc.failure_reason,
	}


def _deliver_email(doc: Any) -> tuple[bool, str]:
	recipient_email = frappe.db.get_value("User", doc.recipient_user, "email")
	if not recipient_email:
		return False, "El usuario destinatario no tiene un correo configurado."
	try:
		frappe.sendmail(
			recipients=[recipient_email],
			subject=doc.subject,
			message=doc.body or "",
			reference_doctype="NXR Notification",
			reference_name=doc.name,
			now=True,
		)
	except Exception as exc:  # noqa: BLE001 -- cualquier fallo de entrega se reporta, nunca se propaga
		return False, str(exc)
	return True, ""


def _deliver_whatsapp(doc: Any) -> tuple[bool, str]:
	external_id = resolve_external_id_for_user(doc.recipient_user)
	if not external_id:
		return False, "El usuario destinatario no tiene un número de WhatsApp vinculado."
	body = f"{doc.subject}\n\n{doc.body}" if doc.body else doc.subject
	try:
		send_direct_message(external_id, body)
	except WhatsAppChannelError as exc:
		return False, str(exc)
	return True, ""


_DELIVERY_HANDLERS = {"Email": _deliver_email, "WhatsApp": _deliver_whatsapp}


def _attempt_delivery(doc: Any, correlation_id: str) -> None:
	"""Intenta la entrega real y registra el resultado real — nunca ``Delivered``
	sin que la llamada correspondiente haya tenido éxito de verdad."""

	if not requires_external_delivery(doc.channel):
		# Inbox/PWA: la propia existencia del registro es la entrega.
		delivered, reason = True, ""
	else:
		delivered, reason = _DELIVERY_HANDLERS[doc.channel](doc)
	with service_write():
		doc.delivery_status = "Delivered" if delivered else "Failed"
		doc.failure_reason = reason
		if delivered:
			doc.delivered_at = frappe.utils.now_datetime()
		doc.save(ignore_permissions=True)
	audit(
		"notification_delivery_attempted",
		"NXR Notification",
		doc.name,
		canonical_payload_hash({"channel": doc.channel, "delivered": delivered}),
		correlation_id,
		_snapshot(doc),
	)


@frappe.whitelist(methods=["POST"])
def create_notification(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("approve")
	channel = data.get("channel", "Inbox")
	priority = data.get("priority", "Normal")
	validate_channel(channel)
	validate_priority(priority)

	idempotency_key = str(data.get("idempotency_key") or "").strip()
	notification_type = data.get("notification_type", "Info")
	body = data.get("body", "")
	recipient_user = data["recipient_user"]
	fingerprint = canonical_payload_hash(
		{
			"subject": data["subject"],
			"body": body,
			"channel": channel,
			"priority": priority,
			"recipient_user": recipient_user,
			"notification_type": notification_type,
			"reference_doctype": data.get("reference_doctype"),
			"reference_name": data.get("reference_name"),
		}
	)

	existing = _existing_by_idempotency_key(idempotency_key)
	if existing:
		existing_doc = frappe.get_doc("NXR Notification", existing)
		if existing_doc.payload_hash != fingerprint:
			frappe.throw(_("La clave de idempotencia ya fue usada con un payload diferente."))
		return _snapshot(existing_doc)

	correlation_id = correlation(data)
	try:
		with service_write():
			notification = frappe.get_doc(
				{
					"doctype": "NXR Notification",
					"subject": data["subject"],
					"body": body,
					"notification_type": notification_type,
					"channel": channel,
					"priority": priority,
					"recipient_user": recipient_user,
					"sender_user": data.get("sender_user"),
					"reference_doctype": data.get("reference_doctype"),
					"reference_name": data.get("reference_name"),
					"delivery_status": "Created",
					"idempotency_key": idempotency_key or None,
					"payload_hash": fingerprint,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
	except frappe.DuplicateEntryError:
		existing = _existing_by_idempotency_key(idempotency_key)
		if not existing:
			raise
		existing_doc = frappe.get_doc("NXR Notification", existing)
		if existing_doc.payload_hash != fingerprint:
			frappe.throw(_("La clave de idempotencia ya fue usada con un payload diferente."))
		return _snapshot(existing_doc)
	audit(
		"notification_created",
		"NXR Notification",
		notification.name,
		canonical_payload_hash({"channel": channel, "recipient_user": data["recipient_user"]}),
		correlation_id,
		_snapshot(notification),
	)
	_attempt_delivery(notification, correlation_id)
	notification.reload()
	return _snapshot(notification)


@frappe.whitelist(methods=["POST"])
def retry_notification(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("approve")
	name = str(data.get("notification") or "").strip()
	if not name:
		frappe.throw(_("Indique qué notificación reintentar."))
	doc = frappe.get_doc("NXR Notification", name)
	if doc.delivery_status != "Failed":
		frappe.throw(_("Solo una notificación fallida puede reintentarse."))
	if not requires_external_delivery(doc.channel):
		frappe.throw(_("Este canal no tiene un paso de entrega que reintentar."))
	if not can_retry_delivery(doc.retry_count or 0):
		frappe.throw(_("Se agotaron los reintentos permitidos para esta notificación."))
	with service_write():
		doc.retry_count = (doc.retry_count or 0) + 1
		doc.save(ignore_permissions=True)
	_attempt_delivery(doc, correlation(data))
	doc.reload()
	return _snapshot(doc)


@frappe.whitelist(methods=["POST"])
def list_notifications(payload: str | Mapping[str, Any]) -> list[dict[str, Any]]:
	data = parse_payload(payload)
	require_action("preview")
	# NXR-SEC-0001 (Bloque 19): antes cualquier rol con "preview" podía leer las
	# notificaciones de OTRO usuario simplemente enviando su `user` — sin ningún
	# llamador real en el producto que lo necesite (no hay ninguna referencia a
	# `list_notifications` en el cliente). Solo un rol con acceso administrativo
	# amplio (`view_all_projects`) puede consultar notificaciones de otro usuario;
	# cualquier otro siempre ve únicamente las suyas, sin importar qué envíe.
	requested_user = str(data.get("user") or "").strip()
	user = requested_user if requested_user and has_action("view_all_projects") else frappe.session.user
	filters = {"recipient_user": user}
	if data.get("channel"):
		filters["channel"] = data["channel"]
	if data.get("read") is not None:
		filters["read"] = data["read"]
	if data.get("delivery_status"):
		filters["delivery_status"] = data["delivery_status"]
	notifications = frappe.get_all(
		"NXR Notification",
		filters=filters,
		fields=[
			"name",
			"document_number",
			"subject",
			"body",
			"notification_type",
			"channel",
			"priority",
			"read",
			"read_on",
			"delivery_status",
			"delivered_at",
			"failure_reason",
			"creation",
		],
		order_by="creation desc",
		limit=data.get("limit", 50),
	)
	return list(notifications)


@frappe.whitelist(methods=["POST"])
def mark_read(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	notification_name = data["notification"]
	notification = frappe.get_doc("NXR Notification", notification_name)
	# Bloque 23: corregido — antes exigía "approve" (solo roles gerenciales),
	# así que el propio destinatario de una notificación no podía marcar la
	# suya como leída. Ahora el destinatario siempre puede marcar la suya;
	# cualquier otro usuario necesita el mismo permiso amplio de siempre.
	if frappe.session.user != notification.recipient_user:
		require_action("approve")
	with service_write():
		notification.read = 1
		notification.read_on = frappe.utils.now()
		notification.save(ignore_permissions=True)
	return {"notification": notification.name, "read": 1}
