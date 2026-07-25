from __future__ import annotations

import json
import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestCloseContract(unittest.TestCase):
	def test_close_module_exists(self) -> None:
		init = APP_ROOT / "close/__init__.py"
		self.assertTrue(init.is_file())

	def test_close_core_exists(self) -> None:
		core = APP_ROOT / "close/core.py"
		self.assertTrue(core.is_file())

	def test_close_service_exists(self) -> None:
		service = APP_ROOT / "close/service.py"
		self.assertTrue(service.is_file())

	def test_monthly_close_doctype_is_defined(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_monthly_close/nxr_monthly_close.json"
		self.assertTrue(path.is_file())
		payload = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual("NXR Monthly Close", payload["name"])

	def test_monthly_close_controller_enforces_boundary(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_monthly_close/nxr_monthly_close.py"
		code = path.read_text(encoding="utf-8")
		self.assertIn("require_service_write", code)
		self.assertIn("on_trash", code)

	def test_monthly_close_has_status_field(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_monthly_close/nxr_monthly_close.json"
		payload = json.loads(path.read_text(encoding="utf-8"))
		field_names = {f["fieldname"] for f in payload["fields"]}
		self.assertIn("status", field_names)
		self.assertIn("project", field_names)
		self.assertIn("close_month", field_names)
		self.assertIn("close_date", field_names)
