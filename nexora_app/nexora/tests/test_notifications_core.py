from __future__ import annotations

from unittest import TestCase

from nexora.notifications.core import (
	MAX_DELIVERY_RETRIES,
	NOTIFICATION_CHANNELS,
	NOTIFICATION_PRIORITIES,
	NotificationError,
	can_retry_delivery,
	render_template,
	requires_external_delivery,
	validate_channel,
	validate_priority,
)


class TestNotificationsCore(TestCase):
	def test_validate_channel_valid_inbox(self) -> None:
		try:
			validate_channel("Inbox")
		except NotificationError:
			self.fail("Inbox deberia ser un canal valido")

	def test_validate_channel_valid_email(self) -> None:
		try:
			validate_channel("Email")
		except NotificationError:
			self.fail("Email deberia ser un canal valido")

	def test_validate_channel_valid_pwa(self) -> None:
		try:
			validate_channel("PWA")
		except NotificationError:
			self.fail("PWA deberia ser un canal valido")

	def test_validate_channel_valid_whatsapp(self) -> None:
		"""Bloque 23: WhatsApp es un canal real de entrega (reutiliza el canal
		del Bloque 21), no solo una etiqueta."""
		try:
			validate_channel("WhatsApp")
		except NotificationError:
			self.fail("WhatsApp deberia ser un canal valido")

	def test_validate_channel_invalid_raises(self) -> None:
		with self.assertRaises(NotificationError):
			validate_channel("SMS")

	def test_validate_channel_empty_raises(self) -> None:
		with self.assertRaises(NotificationError):
			validate_channel("")

	def test_validate_priority_valid_low(self) -> None:
		try:
			validate_priority("Low")
		except NotificationError:
			self.fail("Low deberia ser una prioridad valida")

	def test_validate_priority_valid_normal(self) -> None:
		try:
			validate_priority("Normal")
		except NotificationError:
			self.fail("Normal deberia ser una prioridad valida")

	def test_validate_priority_valid_high(self) -> None:
		try:
			validate_priority("High")
		except NotificationError:
			self.fail("High deberia ser una prioridad valida")

	def test_validate_priority_valid_critical(self) -> None:
		try:
			validate_priority("Critical")
		except NotificationError:
			self.fail("Critical deberia ser una prioridad valida")

	def test_validate_priority_invalid_raises(self) -> None:
		with self.assertRaises(NotificationError):
			validate_priority("Urgent")

	def test_render_template_simple(self) -> None:
		result = render_template("Hola {nombre}", {"nombre": "Mundo"})
		self.assertEqual("Hola Mundo", result)

	def test_render_template_multiple(self) -> None:
		result = render_template("{a} {b} {c}", {"a": "x", "b": "y", "c": "z"})
		self.assertEqual("x y z", result)

	def test_render_template_no_variables(self) -> None:
		result = render_template("texto fijo", {})
		self.assertEqual("texto fijo", result)

	def test_notification_channels_are_known(self) -> None:
		self.assertIn("Inbox", NOTIFICATION_CHANNELS)
		self.assertIn("Email", NOTIFICATION_CHANNELS)
		self.assertIn("PWA", NOTIFICATION_CHANNELS)
		self.assertIn("WhatsApp", NOTIFICATION_CHANNELS)
		self.assertEqual(4, len(NOTIFICATION_CHANNELS))

	def test_notification_priorities_are_known(self) -> None:
		self.assertIn("Low", NOTIFICATION_PRIORITIES)
		self.assertIn("Normal", NOTIFICATION_PRIORITIES)
		self.assertIn("High", NOTIFICATION_PRIORITIES)
		self.assertIn("Critical", NOTIFICATION_PRIORITIES)
		self.assertEqual(4, len(NOTIFICATION_PRIORITIES))

	def test_inbox_and_pwa_do_not_require_external_delivery(self) -> None:
		"""La bandeja (app o PWA instalada) ES el mecanismo de entrega: no hay un
		segundo paso de red que pueda fallar aparte de crear el registro."""
		self.assertFalse(requires_external_delivery("Inbox"))
		self.assertFalse(requires_external_delivery("PWA"))

	def test_email_and_whatsapp_require_external_delivery(self) -> None:
		"""Email y WhatsApp exigen una llamada real a un canal externo que puede
		fallar de verdad, por lo que tienen su propio intento de entrega."""
		self.assertTrue(requires_external_delivery("Email"))
		self.assertTrue(requires_external_delivery("WhatsApp"))

	def test_can_retry_delivery_below_the_maximum(self) -> None:
		self.assertTrue(can_retry_delivery(0))
		self.assertTrue(can_retry_delivery(MAX_DELIVERY_RETRIES - 1))

	def test_can_retry_delivery_at_or_above_the_maximum_is_rejected(self) -> None:
		self.assertFalse(can_retry_delivery(MAX_DELIVERY_RETRIES))
		self.assertFalse(can_retry_delivery(MAX_DELIVERY_RETRIES + 1))
