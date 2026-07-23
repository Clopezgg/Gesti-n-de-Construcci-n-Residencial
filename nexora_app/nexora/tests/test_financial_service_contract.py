from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVICE_FILES = [
	ROOT / f"nexora/financial/{name}.py" for name in ("db", "operations", "sources", "commitments", "service")
]
PERMISSIONS = ROOT / "nexora/permissions.py"


def service_text() -> str:
	return "\n".join(path.read_text(encoding="utf-8") for path in SERVICE_FILES)


class TestFinancialServiceContract(unittest.TestCase):
	def test_server_services_are_post_only_and_permission_guarded(self) -> None:
		text = service_text()
		self.assertGreaterEqual(text.count('@frappe.whitelist(methods=["POST"])'), 7)
		self.assertIn("require_action(action)", text)
		self.assertIn('require_action("create_source")', text)

	def test_stable_locking_and_savepoint_rollback_are_explicit(self) -> None:
		text = service_text()
		self.assertIn(".orderby(source.name)", text)
		self.assertIn(".for_update()", text)
		self.assertIn("frappe.db.savepoint(name)", text)
		self.assertIn("frappe.db.rollback(save_point=name)", text)
		self.assertNotIn("frappe.db.commit()", text)

	def test_idempotency_payload_conflict_is_rejected(self) -> None:
		text = service_text()
		self.assertIn("record.payload_hash != fingerprint", text)
		self.assertIn("payload diferente", text)

	def test_permissions_are_server_side_and_auditor_cannot_execute(self) -> None:
		text = PERMISSIONS.read_text(encoding="utf-8")
		execute_line = next(line for line in text.splitlines() if '"execute":' in line)
		self.assertNotIn("NEXORA Auditor", execute_line)
		self.assertIn("frappe.PermissionError", text)

	def test_canonical_documents_require_orchestrator_context(self) -> None:
		for relative in (
			"nexora/nexora/doctype/nxr_fund_source/nxr_fund_source.py",
			"nexora/nexora/doctype/nxr_operation/nxr_operation.py",
			"nexora/nexora/doctype/nxr_commitment/nxr_commitment.py",
		):
			text = (ROOT / relative).read_text(encoding="utf-8")
			self.assertIn("require_service_write()", text, relative)
		text = service_text()
		self.assertGreaterEqual(text.count("with service_write():"), 5)

	def test_no_legacy_ledger_write_and_no_partial_commit(self) -> None:
		text = service_text()
		self.assertNotIn("CC Material Ledger", text)
		self.assertNotIn("frappe.db.commit", text)


if __name__ == "__main__":
	unittest.main()
