from __future__ import annotations

import json
import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestProgressContract(unittest.TestCase):
	def test_progress_module_exists(self) -> None:
		init = APP_ROOT / "progress/__init__.py"
		self.assertTrue(init.is_file())

	def test_progress_core_exists(self) -> None:
		core = APP_ROOT / "progress/core.py"
		self.assertTrue(core.is_file())

	def test_progress_service_exists(self) -> None:
		service = APP_ROOT / "progress/service.py"
		self.assertTrue(service.is_file())

	def test_progress_record_doctype_is_defined(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_progress_record/nxr_progress_record.json"
		self.assertTrue(path.is_file())
		payload = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual("NXR Progress Record", payload["name"])

	def test_quality_check_doctype_is_defined(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_quality_check/nxr_quality_check.json"
		self.assertTrue(path.is_file())
		payload = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual("NXR Quality Check", payload["name"])

	def test_progress_record_controller_enforces_boundary(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_progress_record/nxr_progress_record.py"
		code = path.read_text(encoding="utf-8")
		self.assertIn("require_service_write", code)
		self.assertIn("on_trash", code)

	def test_quality_check_controller_enforces_boundary(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_quality_check/nxr_quality_check.py"
		code = path.read_text(encoding="utf-8")
		self.assertIn("require_service_write", code)
		self.assertIn("on_trash", code)
