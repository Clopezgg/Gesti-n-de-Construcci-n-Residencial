from __future__ import annotations

import json
import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestBudgetContract(unittest.TestCase):
	def test_budget_module_exists(self) -> None:
		init = APP_ROOT / "budget/__init__.py"
		self.assertTrue(init.is_file())

	def test_budget_core_exists(self) -> None:
		core = APP_ROOT / "budget/core.py"
		self.assertTrue(core.is_file())

	def test_budget_service_exists(self) -> None:
		service = APP_ROOT / "budget/service.py"
		self.assertTrue(service.is_file())

	def test_budget_doctype_is_defined(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_budget/nxr_budget.json"
		self.assertTrue(path.is_file())
		payload = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual("NXR Budget", payload["name"])

	def test_budget_controller_enforces_boundary(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_budget/nxr_budget.py"
		code = path.read_text(encoding="utf-8")
		self.assertIn("require_service_write", code)
		self.assertIn("on_trash", code)

	def test_budget_line_is_table(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_budget_line/nxr_budget_line.json"
		self.assertTrue(path.is_file())
		payload = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual("NXR Budget Line", payload["name"])
		self.assertEqual(1, payload["istable"])

	def test_budget_line_has_balance_fields(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_budget_line/nxr_budget_line.json"
		payload = json.loads(path.read_text(encoding="utf-8"))
		field_names = {f["fieldname"] for f in payload["fields"]}
		for field in ("economic_category", "approved_hnl", "committed_hnl", "executed_hnl", "available_hnl"):
			self.assertIn(field, field_names)
