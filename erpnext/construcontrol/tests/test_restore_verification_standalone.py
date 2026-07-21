from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "erpnext" / "construcontrol" / "migration" / "restore_verification.py"


class _FakeDB:
	def __init__(self) -> None:
		self.counted: list[str] = []

	def exists(self, doctype: str, name: str) -> bool:
		return doctype == "DocType" and name == "Project"

	def count(self, doctype: str) -> int:
		self.counted.append(doctype)
		return 0


class _ValidationError(Exception):
	pass


def _load_module():
	fake_frappe = types.ModuleType("frappe")
	fake_frappe.db = _FakeDB()
	fake_frappe.ValidationError = _ValidationError
	previous = sys.modules.get("frappe")
	sys.modules["frappe"] = fake_frappe
	try:
		spec = importlib.util.spec_from_file_location("cc_restore_verification_test", MODULE)
		assert spec and spec.loader
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
	finally:
		if previous is None:
			sys.modules.pop("frappe", None)
		else:
			sys.modules["frappe"] = previous
	return module, fake_frappe


class RestoreVerificationStandaloneTest(unittest.TestCase):
	def test_zero_count_remains_a_truthy_serializable_payload(self) -> None:
		module, fake_frappe = _load_module()
		result = module.count_records(" Project ")
		self.assertEqual(result, {"doctype": "Project", "count": 0})
		self.assertEqual(fake_frappe.db.counted, ["Project"])
		self.assertTrue(result)

	def test_unknown_doctype_is_rejected_before_counting(self) -> None:
		module, fake_frappe = _load_module()
		with self.assertRaises(_ValidationError):
			module.count_records("Missing DocType")
		self.assertEqual(fake_frappe.db.counted, [])


if __name__ == "__main__":
	unittest.main()
