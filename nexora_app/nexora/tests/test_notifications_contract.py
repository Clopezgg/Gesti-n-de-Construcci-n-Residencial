from __future__ import annotations

import json
import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


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
