"""NXR-NOT-0006: entrega real de notificaciones contra Frappe/MariaDB (Bloque 23).

Requiere bench + MariaDB reales; no se pudo ejecutar en el entorno de esta
sesión (sin bench/Frappe/MariaDB — confirmado por
``ModuleNotFoundError: No module named 'frappe'`` al intentar importarlo
aquí). Los intentos reales de entrega externa se simulan con
``unittest.mock.patch`` sobre ``frappe.sendmail`` (Email) y sobre
``nexora.conversation.channels.whatsapp.send_direct_message``/
``resolve_external_id_for_user`` (WhatsApp) — nunca sobre las funciones puras
de ``notifications.core``, que ya se prueban de verdad sin necesitar Frappe en
``test_notifications_core.py``.

Cobertura pensada para la matriz mínima honesta de este bloque: Inbox/PWA se
marcan entregados al crearse sin ninguna llamada externa, Email/WhatsApp
exitoso marca Delivered solo tras una llamada real exitosa, Email/WhatsApp
fallido marca Failed con el motivo real (nunca un éxito fabricado), reintento
tras fallo puede tener éxito y se limita a ``MAX_DELIVERY_RETRIES``, una clave
de idempotencia repetida devuelve el registro existente sin reintentar la
entrega, el propio destinatario puede marcar su notificación como leída sin
un rol gerencial, y un tercero sin rol amplio no puede leer notificaciones de
otro usuario.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.conversation.channels.whatsapp import WhatsAppChannelError
from nexora.notifications import service
from nexora.notifications.core import MAX_DELIVERY_RETRIES


def _key(prefix: str) -> str:
	return f"{prefix}-{uuid.uuid4().hex}"


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


class TestNotificationDeliveryIntegrationMariaDB(FrappeTestCase):
	def setUp(self) -> None:
		frappe.set_user("Administrator")
		self.recipient = _ensure_user(_key("notif-recipient") + "@example.com", "NEXORA Finance Operator")
		self.other_user = _ensure_user(_key("notif-other") + "@example.com", "NEXORA Project Viewer")
		frappe.db.set_value("User", self.recipient, "email", self.recipient)

	def _create(self, **overrides) -> dict:
		payload = {
			"subject": "Asunto de prueba",
			"body": "Cuerpo de prueba",
			"recipient_user": self.recipient,
			"channel": "Inbox",
		}
		payload.update(overrides)
		return service.create_notification(payload)

	def test_inbox_notification_is_delivered_immediately_without_any_external_call(self) -> None:
		with patch("frappe.sendmail") as mock_sendmail:
			result = self._create(channel="Inbox")
			mock_sendmail.assert_not_called()
		self.assertEqual("Delivered", result["delivery_status"])

	def test_pwa_notification_is_delivered_immediately_without_any_external_call(self) -> None:
		with patch("frappe.sendmail") as mock_sendmail:
			result = self._create(channel="PWA")
			mock_sendmail.assert_not_called()
		self.assertEqual("Delivered", result["delivery_status"])

	def test_email_notification_is_delivered_only_after_a_real_successful_sendmail_call(self) -> None:
		with patch("frappe.sendmail") as mock_sendmail:
			result = self._create(channel="Email")
			mock_sendmail.assert_called_once()
			self.assertEqual(self.recipient, mock_sendmail.call_args.kwargs["recipients"][0])
		self.assertEqual("Delivered", result["delivery_status"])

	def test_email_notification_is_marked_failed_when_sendmail_raises_never_a_fabricated_success(
		self,
	) -> None:
		with patch("frappe.sendmail", side_effect=Exception("SMTP caído en esta prueba")):
			result = self._create(channel="Email")
		self.assertEqual("Failed", result["delivery_status"])
		self.assertIn("SMTP caído", result["failure_reason"])

	def test_whatsapp_notification_is_delivered_only_after_a_real_successful_send(self) -> None:
		with (
			patch("nexora.notifications.service.resolve_external_id_for_user", return_value="50411111111"),
			patch("nexora.notifications.service.send_direct_message") as mock_send,
		):
			result = self._create(channel="WhatsApp")
			mock_send.assert_called_once()
		self.assertEqual("Delivered", result["delivery_status"])

	def test_whatsapp_notification_fails_honestly_when_the_recipient_has_no_linked_number(self) -> None:
		with patch("nexora.notifications.service.resolve_external_id_for_user", return_value=None):
			result = self._create(channel="WhatsApp")
		self.assertEqual("Failed", result["delivery_status"])
		self.assertIn("no tiene un número de WhatsApp vinculado", result["failure_reason"])

	def test_whatsapp_notification_fails_honestly_when_meta_rejects_the_send(self) -> None:
		with (
			patch("nexora.notifications.service.resolve_external_id_for_user", return_value="50411111111"),
			patch(
				"nexora.notifications.service.send_direct_message",
				side_effect=WhatsAppChannelError("Meta rechazó el envío en esta prueba"),
			),
		):
			result = self._create(channel="WhatsApp")
		self.assertEqual("Failed", result["delivery_status"])
		self.assertIn("Meta rechazó el envío", result["failure_reason"])

	def test_retry_after_failure_can_succeed_and_increments_retry_count(self) -> None:
		with patch("frappe.sendmail", side_effect=Exception("primer intento falla")):
			created = self._create(channel="Email")
		self.assertEqual("Failed", created["delivery_status"])
		with patch("frappe.sendmail") as mock_sendmail:
			retried = service.retry_notification({"notification": created["notification"]})
			mock_sendmail.assert_called_once()
		self.assertEqual("Delivered", retried["delivery_status"])
		doc = frappe.get_doc("NXR Notification", created["notification"])
		self.assertEqual(1, doc.retry_count)

	def test_retry_is_capped_at_the_maximum_and_then_rejected(self) -> None:
		with patch("frappe.sendmail", side_effect=Exception("siempre falla en esta prueba")):
			created = self._create(channel="Email")
			for _ in range(MAX_DELIVERY_RETRIES):
				service.retry_notification({"notification": created["notification"]})
			with self.assertRaises(frappe.ValidationError):
				service.retry_notification({"notification": created["notification"]})

	def test_retry_rejects_a_channel_without_an_external_delivery_step(self) -> None:
		created = self._create(channel="Inbox")
		with self.assertRaises(frappe.ValidationError):
			service.retry_notification({"notification": created["notification"]})

	def test_duplicate_idempotency_key_returns_the_existing_record_without_re_delivering(self) -> None:
		key = _key("idem")
		with patch("frappe.sendmail") as mock_sendmail:
			first = self._create(channel="Email", idempotency_key=key)
			second = self._create(channel="Email", idempotency_key=key)
			mock_sendmail.assert_called_once()
		self.assertEqual(first["notification"], second["notification"])

	def test_recipient_can_mark_their_own_notification_read_without_a_managerial_role(self) -> None:
		created = self._create(channel="Inbox")
		frappe.set_user(self.recipient)
		try:
			result = service.mark_read({"notification": created["notification"]})
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(1, result["read"])

	def test_a_third_party_without_broad_role_cannot_read_another_users_notifications(self) -> None:
		self._create(channel="Inbox")
		frappe.set_user(self.other_user)
		try:
			results = service.list_notifications({"user": self.recipient})
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(0, len(results))
