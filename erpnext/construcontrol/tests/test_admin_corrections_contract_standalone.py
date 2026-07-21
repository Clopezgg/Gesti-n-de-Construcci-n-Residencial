from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "erpnext" / "construcontrol" / "admin_corrections.py"
SECURITY = ROOT / "erpnext" / "construcontrol" / "admin_correction_security.py"
EXPENSES = ROOT / "erpnext" / "construcontrol" / "admin_expense_operations.py"
SUPPLIERS = ROOT / "erpnext" / "construcontrol" / "admin_supplier_corrections.py"
USERS = ROOT / "erpnext" / "construcontrol" / "admin_user_corrections.py"
RECORDS = ROOT / "erpnext" / "construcontrol" / "admin_record_corrections.py"
SETUP = ROOT / "erpnext" / "construcontrol" / "admin_correction_setup.py"
PROFILE = ROOT / "erpnext" / "construcontrol" / "profile.py"
PROFILE_JS = (
	ROOT / "erpnext" / "construcontrol" / "page" / "construcontrol_profile" / "construcontrol_profile.js"
)
CENTER_JS = ROOT / "erpnext" / "public" / "js" / "construcontrol_admin_corrections.js"
MIGRATION_PAGE = (
	ROOT
	/ "erpnext"
	/ "construcontrol"
	/ "page"
	/ "construcontrol_migration_console"
	/ "construcontrol_migration_console.js"
)
HOOKS = ROOT / "erpnext" / "hooks.py"
ACCESS = ROOT / "erpnext" / "construcontrol" / "access.py"
INSTALL = ROOT / "erpnext" / "construcontrol" / "install.py"


class AdministratorCorrectionContractTest(unittest.TestCase):
	@classmethod
	def setUpClass(cls) -> None:
		cls.core = CORE.read_text(encoding="utf-8")
		cls.security = SECURITY.read_text(encoding="utf-8")
		cls.expenses = EXPENSES.read_text(encoding="utf-8")
		cls.suppliers = SUPPLIERS.read_text(encoding="utf-8")
		cls.users = USERS.read_text(encoding="utf-8")
		cls.records = RECORDS.read_text(encoding="utf-8")
		cls.setup = SETUP.read_text(encoding="utf-8")
		cls.profile = PROFILE.read_text(encoding="utf-8")
		cls.profile_js = PROFILE_JS.read_text(encoding="utf-8")
		cls.center_js = CENTER_JS.read_text(encoding="utf-8")
		cls.migration_page = MIGRATION_PAGE.read_text(encoding="utf-8")
		cls.hooks = HOOKS.read_text(encoding="utf-8")
		cls.access = ACCESS.read_text(encoding="utf-8")
		cls.install = INSTALL.read_text(encoding="utf-8")

	def test_only_administrator_can_open_the_critical_context(self) -> None:
		self.assertIn('frappe.session.user or "") != "Administrator"', self.core)
		self.assertIn('frappe.session.user or "") != "Administrator"', self.access)
		self.assertIn("Solo la cuenta Administrator", self.core)
		self.assertNotIn("ConstruControl Manager puede ejecutar correcciones", self.core)

	def test_pin_is_hashed_hidden_and_never_returned_by_profile(self) -> None:
		self.assertIn("passlibctx.hash", self.security)
		self.assertIn('"correction_pin_hash"', self.setup)
		self.assertIn("hidden=1", self.setup)
		self.assertIn("no_copy=1", self.setup)
		self.assertNotIn('"pin": _get', self.core)
		self.assertNotIn("correction_pin_hash", self.profile)
		self.assertNotIn("correction_pin_hash", self.profile_js)

	def test_failed_attempts_are_committed_before_the_authentication_error(self) -> None:
		self.assertIn("frappe.db.commit()", self.security)
		self.assertIn("CORRECTION_AUTH_FAILED", self.security)
		self.assertIn("correction_locked_until", self.security)
		self.assertIn("override_whitelisted_methods", self.hooks)
		self.assertIn("admin_correction_security.authorize_correction", self.hooks)

	def test_authorization_is_short_lived_session_bound_and_not_browser_persistent(self) -> None:
		self.assertIn("_AUTH_TTL = 600", self.core)
		self.assertIn('"session_id": _session_id()', self.security)
		self.assertIn("expires_in_sec=_AUTH_TTL", self.security)
		self.assertNotIn("localStorage", self.center_js)
		self.assertNotIn("sessionStorage", self.center_js)
		self.assertNotIn("document.cookie", self.center_js)

	def test_financial_changes_require_private_evidence_and_preview_hash(self) -> None:
		self.assertIn("is_private", self.core)
		self.assertIn("_FINANCIAL_FIELDS", self.core)
		self.assertIn("preview_hash", self.core)
		self.assertIn("compare_digest", self.expenses)
		self.assertIn("previewThenExecute", self.center_js)
		self.assertIn("is_private: 1", self.center_js)

	def test_expense_operations_are_atomic_and_recalculate_relations(self) -> None:
		for marker in (
			"frappe.db.savepoint",
			"frappe.db.rollback(save_point=savepoint)",
			"frappe.cache.lock",
			"sync_payable_from_expense",
			"_recalculate(before, after)",
			"ADMIN_EXPENSE_BATCH",
		):
			self.assertIn(marker, self.expenses)
		self.assertIn("_MAX_BATCH = 50", self.expenses)
		self.assertNotIn("frappe.db.sql", self.expenses)

	def test_supplier_consolidation_archives_instead_of_deleting_business_records(self) -> None:
		self.assertIn('"cc_merged_into": canonical', self.suppliers)
		self.assertIn('"cc_archived_duplicate": 1', self.suppliers)
		self.assertIn('"disabled": 1', self.suppliers)
		self.assertIn("unsupported_count", self.suppliers)
		self.assertNotIn('delete_doc("Supplier"', self.suppliers)
		self.assertNotIn("ConstruControl Legacy Record", self.suppliers)

	def test_user_correction_preserves_authorship_and_protected_accounts(self) -> None:
		self.assertIn('_PROTECTED = {"Administrator", "Guest"}', self.users)
		self.assertIn("historical_owner_modified_by_unchanged", self.users)
		self.assertIn("historical_authorship_preserved", self.users)
		self.assertIn('"enabled": 0', self.users)
		self.assertNotIn('delete_doc("User"', self.users)
		self.assertNotIn("update_owner", self.users)
		self.assertNotIn("update_modified_by", self.users)

	def test_fi01_phase_contract_and_payable_have_allowlisted_workflows(self) -> None:
		for doctype in ("CC Funding Source", "CC Construction Phase", "CC Labor Contract"):
			self.assertIn(doctype, self.records)
		self.assertIn("_SCHEMAS", self.records)
		self.assertIn("Campos no autorizados", self.records)
		self.assertIn("preview_payable_rebuild", self.records)
		self.assertIn("execute_payable_rebuild", self.records)
		self.assertNotIn("frappe.db.sql", self.records)

	def test_original_history_and_audit_are_not_delete_targets(self) -> None:
		combined = "\n".join((self.core, self.expenses, self.suppliers, self.users, self.records))
		self.assertNotIn('delete_doc("ConstruControl Legacy Record"', combined)
		self.assertNotIn('delete_doc("CC Audit Log"', combined)
		self.assertNotIn('delete_doc("CC Immutable Audit Event"', combined)
		self.assertIn("record_manual_event", combined)
		self.assertIn('origin="ADMIN_CORRECTION"', combined)

	def test_install_and_mobile_center_are_additive(self) -> None:
		self.assertIn("ensure_admin_correction_fields", self.install)
		self.assertIn("construcontrol_admin_corrections.js", self.hooks)
		self.assertIn("ConstruControlAdminCorrections?.mount(body)", self.migration_page)
		self.assertIn("max-width:767px", self.center_js)
		self.assertIn('frappe.session.user !== "Administrator"', self.center_js)


if __name__ == "__main__":
	unittest.main()
