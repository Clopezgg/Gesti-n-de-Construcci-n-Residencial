from __future__ import annotations

import json
import pathlib
import re
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


def function_body(source: str, name: str) -> str:
	match = re.search(rf"\ndef {re.escape(name)}\(.*?\n(?=\n@|\ndef |\Z)", source, flags=re.DOTALL)
	if not match:
		raise AssertionError(f"no se encontró la función {name!r}")
	return match.group(0)


class TestNotificationsContract(unittest.TestCase):
	def test_notification_module_exists(self) -> None:
		init = APP_ROOT / "notifications/__init__.py"
		self.assertTrue(init.is_file())

	def test_notification_core_exists(self) -> None:
		core = APP_ROOT / "notifications/core.py"
		self.assertTrue(core.is_file())

	def test_notification_service_exists(self) -> None:
		service = APP_ROOT / "notifications/service.py"
		self.assertTrue(service.is_file())

	def test_notification_doctype_is_defined(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_notification/nxr_notification.json"
		self.assertTrue(path.is_file())
		payload = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual("NXR Notification", payload["name"])

	def test_notification_controller_enforces_boundary(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_notification/nxr_notification.py"
		code = path.read_text(encoding="utf-8")
		self.assertIn("require_service_write", code)
		self.assertIn("on_trash", code)

	def test_notification_preference_is_table(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_notification_preference/nxr_notification_preference.json"
		self.assertTrue(path.is_file())
		payload = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual("NXR Notification Preference", payload["name"])
		self.assertEqual(1, payload["istable"])

	def test_notification_preference_has_user_field(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_notification_preference/nxr_notification_preference.json"
		payload = json.loads(path.read_text(encoding="utf-8"))
		field_names = {f["fieldname"] for f in payload["fields"]}
		self.assertIn("user", field_names)
		self.assertIn("channel_enabled", field_names)
		self.assertIn("min_priority", field_names)


class TestNotificationDeliveryFields(unittest.TestCase):
	"""Bloque 23 (NXR-NOT-0006): el doctype debe distinguir de verdad
	Creado/Entregado/Fallido, no solo declarar un estado fijo."""

	def payload(self) -> dict:
		path = APP_ROOT / "nexora/doctype/nxr_notification/nxr_notification.json"
		return json.loads(path.read_text(encoding="utf-8"))

	def test_channel_includes_whatsapp(self) -> None:
		by_name = {f["fieldname"]: f for f in self.payload()["fields"]}
		self.assertIn("WhatsApp", by_name["channel"]["options"].split("\n"))

	def test_delivery_status_field_is_a_real_tri_state(self) -> None:
		by_name = {f["fieldname"]: f for f in self.payload()["fields"]}
		field = by_name["delivery_status"]
		self.assertEqual({"Created", "Delivered", "Failed"}, set(field["options"].split("\n")))
		self.assertEqual("Created", field["default"])

	def test_delivery_bookkeeping_fields_exist_and_are_read_only(self) -> None:
		by_name = {f["fieldname"]: f for f in self.payload()["fields"]}
		for fieldname in ("delivered_at", "failure_reason", "retry_count"):
			with self.subTest(field=fieldname):
				self.assertEqual(1, by_name[fieldname].get("read_only"), fieldname)


class TestNotificationServiceRealDelivery(unittest.TestCase):
	"""Bloque 23: `create_notification` debe intentar una entrega real y nunca
	fabricar un `Delivered` — Email usa `frappe.sendmail` real, WhatsApp
	reutiliza el canal real del Bloque 21."""

	def source(self) -> str:
		return (APP_ROOT / "notifications/service.py").read_text(encoding="utf-8")

	def test_email_delivery_uses_the_real_frappe_sendmail_not_a_fake_success(self) -> None:
		source = self.source()
		body = function_body(source, "_deliver_email")
		self.assertIn("frappe.sendmail(", body)
		self.assertIn("except Exception", body)

	def test_whatsapp_delivery_reuses_the_real_bloque_21_channel(self) -> None:
		source = self.source()
		self.assertIn("from nexora.conversation.channels.whatsapp import", source)
		self.assertIn("send_direct_message", source)
		self.assertIn("resolve_external_id_for_user", source)
		body = function_body(source, "_deliver_whatsapp")
		self.assertIn("send_direct_message(", body)

	def test_delivery_status_is_only_ever_set_from_a_real_outcome(self) -> None:
		source = self.source()
		body = function_body(source, "_attempt_delivery")
		self.assertIn('"Delivered" if delivered else "Failed"', body)

	def test_create_and_retry_and_mark_read_are_whitelisted_post_endpoints(self) -> None:
		source = self.source()
		for name in ("create_notification", "retry_notification", "mark_read"):
			with self.subTest(function=name):
				pattern = rf'@frappe\.whitelist\(methods=\["POST"\]\)\ndef {re.escape(name)}\('
				self.assertRegex(source, pattern)

	def test_create_notification_validates_channel_and_priority(self) -> None:
		source = self.source()
		body = function_body(source, "create_notification")
		self.assertIn("validate_channel(channel)", body)
		self.assertIn("validate_priority(priority)", body)

	def test_create_notification_deduplicates_by_idempotency_key(self) -> None:
		"""Antes un reintento del propio llamador con la misma clave habría
		chocado contra la restricción `unique=1` del campo con un error crudo de
		base de datos en vez de devolver el registro ya existente."""
		source = self.source()
		body = function_body(source, "create_notification")
		self.assertIn("_existing_by_idempotency_key(", body)

	def test_retry_notification_only_allows_failed_channels_with_external_delivery(self) -> None:
		source = self.source()
		body = function_body(source, "retry_notification")
		self.assertIn('doc.delivery_status != "Failed"', body)
		self.assertIn("requires_external_delivery(doc.channel)", body)
		self.assertIn("can_retry_delivery(", body)

	def test_mark_read_lets_the_real_recipient_mark_their_own_notification(self) -> None:
		"""Corregido en el Bloque 23: antes exigía `approve` (rol gerencial)
		incluso para que el propio destinatario marcara su notificación como
		leída."""
		source = self.source()
		body = function_body(source, "mark_read")
		self.assertIn("frappe.session.user != notification.recipient_user", body)

	def test_list_notifications_restricts_cross_user_reads_to_broad_role(self) -> None:
		"""Regresión directa de NXR-SEC-0001 (Bloque 19)."""
		source = self.source()
		body = function_body(source, "list_notifications")
		self.assertIn('has_action("view_all_projects")', body)

	def test_administrative_delivery_attempts_are_audited(self) -> None:
		source = self.source()
		for name in ("create_notification", "_attempt_delivery"):
			with self.subTest(function=name):
				body = function_body(source, name)
				self.assertIn("audit(", body)
