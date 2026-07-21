from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
IMPORTER = ROOT / "erpnext" / "construcontrol" / "migration" / "importer.py"
INSTALL = ROOT / "erpnext" / "construcontrol" / "install.py"
SCHEMA_STATE = ROOT / "erpnext" / "construcontrol" / "schema_state.py"


class MigrationSafetyContractTest(unittest.TestCase):
	@classmethod
	def setUpClass(cls) -> None:
		cls.importer_text = IMPORTER.read_text(encoding="utf-8")
		cls.install_text = INSTALL.read_text(encoding="utf-8")
		cls.schema_state_text = SCHEMA_STATE.read_text(encoding="utf-8")

	def test_migration_is_serialized_with_database_lock(self) -> None:
		self.assertIn("SELECT GET_LOCK(%s, %s)", self.importer_text)
		self.assertIn("SELECT RELEASE_LOCK(%s)", self.importer_text)
		self.assertIn("_exclusive_migration_lock", self.importer_text)

	def test_duplicate_users_are_preserved_not_deleted(self) -> None:
		self.assertIn("duplicate_doc.is_logically_deleted = 1", self.importer_text)
		self.assertIn('"hard_deleted": 0', self.importer_text)
		self.assertNotIn('frappe.delete_doc("CC User Access"', self.importer_text)
		self.assertNotIn("force=True", self.importer_text)

	def test_runtime_contract_precedes_database_mutation(self) -> None:
		validation = self.install_text.index("_validate_runtime_definitions()")
		roles = self.install_text.index("_ensure_roles()", validation)
		self.assertLess(validation, roles)
		self.assertIn("validate_runtime_contract_or_raise", self.install_text)

	def test_contract_state_is_recorded_only_after_schema_installation(self) -> None:
		integration = self.install_text.index("_run_page_integrations_safely(")
		recording = self.install_text.index("record_runtime_contract(runtime_report)")
		self.assertLess(integration, recording)
		self.assertIn("runtime_contract_sha256", self.schema_state_text)
		self.assertIn("runtime_contract_validated_at", self.schema_state_text)
		self.assertIn('if not report.get("ok")', self.schema_state_text)


if __name__ == "__main__":
	unittest.main()
