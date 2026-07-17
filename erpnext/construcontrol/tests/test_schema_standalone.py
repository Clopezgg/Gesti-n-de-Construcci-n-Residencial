from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "migration" / "schema.py"
SPEC = importlib.util.spec_from_file_location("construcontrol_schema_test", SCHEMA_PATH)
assert SPEC and SPEC.loader
schema = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = schema
SPEC.loader.exec_module(schema)


class ConstruControlSchemaTest(unittest.TestCase):
	def snapshot(self):
		return {
			"settings": {"projectName": "Casa", "pinHash": "must-not-migrate"},
			"phases": [{"id": "phase-1", "name": "Foundation"}],
			"incomes": [{"id": "income-1", "amountHnl": 100}],
			"expenses": [
				{"id": "expense-1", "phaseId": "phase-1", "paymentSourceId": "income-1", "amountHnl": 20}
			],
			"laborContracts": [],
			"materials": [],
			"inventoryMovements": [],
			"progressUpdates": [],
			"weeklyClosings": [],
			"reports": [],
			"notificationContacts": [],
			"notificationRules": [],
			"notificationLogs": [],
			"auditLogs": [],
			"userAccounts": [],
		}

	def test_native_and_supabase_shapes(self):
		native = schema.normalize_export_document(self.snapshot())
		wrapped = schema.normalize_export_document({"rows": [{"project_id": "p-1", "data": self.snapshot()}]})
		self.assertEqual(len(native), 1)
		self.assertEqual(wrapped[0].project_key, "p-1")

	def test_valid_references(self):
		report = schema.preflight_snapshot(self.snapshot())
		self.assertEqual(report["error_count"], 0)
		self.assertEqual(report["counts"]["expenses"], 1)

	def test_orphans_and_duplicates_are_reported(self):
		snapshot = self.snapshot()
		snapshot["expenses"].append({"id": "expense-1", "phaseId": "missing", "paymentSourceId": "income-1"})
		report = schema.preflight_snapshot(snapshot)
		codes = {issue["code"] for issue in report["issues"]}
		self.assertIn("duplicate_source_id", codes)
		self.assertIn("orphan_reference", codes)

	def test_sensitive_values_are_removed(self):
		cleaned, count = schema.sanitize_payload({"pinHash": "x", "nested": {"passwordHash": "y", "ok": 1}})
		self.assertEqual(count, 2)
		self.assertNotIn("pinHash", cleaned)
		self.assertEqual(cleaned["nested"], {"ok": 1})

	def test_versioned_key_is_idempotent(self):
		digest = schema.sha256_json({"id": "a", "value": 1})
		first = schema.versioned_record_key("p", "expenses", "a", digest)
		second = schema.versioned_record_key("p", "expenses", "a", digest)
		self.assertEqual(first, second)


if __name__ == "__main__":
	unittest.main()
