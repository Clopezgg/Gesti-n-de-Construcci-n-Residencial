from __future__ import annotations

import json
import pathlib
import unittest

APP_ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKAGE = APP_ROOT / "nexora"


class TestEvidenceContract(unittest.TestCase):
	def test_evidence_doctype_is_private_immutable_and_non_deletable(self) -> None:
		root = PACKAGE / "nexora/doctype/nxr_evidence"
		definition = json.loads((root / "nxr_evidence.json").read_text(encoding="utf-8"))
		controller = (root / "nxr_evidence.py").read_text(encoding="utf-8")
		self.assertEqual("NEXORA", definition["module"])
		fields = {row["fieldname"]: row for row in definition["fields"]}
		for fieldname in (
			"document_number",
			"file_url",
			"content_sha256",
			"version",
			"supersedes",
			"idempotency_key",
			"correlation_id",
		):
			self.assertIn(fieldname, fields)
		self.assertTrue(all(not row.get("delete") for row in definition["permissions"]))
		self.assertTrue(all(not row.get("create") for row in definition["permissions"]))
		self.assertIn("require_service_write()", controller)
		self.assertIn("def on_trash", controller)
		self.assertIn("assert_evidence_transition", controller)

	def test_executed_operation_has_state_and_field_immutability(self) -> None:
		controller = (PACKAGE / "nexora/doctype/nxr_operation/nxr_operation.py").read_text(encoding="utf-8")
		self.assertIn('"Executed": {"Compensated Partial", "Compensated Total"}', controller)
		self.assertIn("IMMUTABLE_EXECUTED_FIELDS", controller)
		self.assertIn("La operación ejecutada es inmutable", controller)
		self.assertIn("documento compensatorio", controller)

	def test_evidence_services_are_exported_and_ui_connected(self) -> None:
		service = (PACKAGE / "financial/service.py").read_text(encoding="utf-8")
		page = (PACKAGE / "nexora/page/nexora_evidence/nexora_evidence.js").read_text(encoding="utf-8")
		for name in ("register_evidence", "review_evidence", "list_evidence"):
			self.assertIn(name, service)
			self.assertIn(f"nexora.financial.service.{name}", page)
		self.assertIn("SHA-256", page)
		self.assertIn("WhatsApp", page)

	def test_policy_requires_canonical_whatsapp_record_for_special_authorization(self) -> None:
		service = (PACKAGE / "financial/evidence.py").read_text(encoding="utf-8")
		self.assertIn("requires_external_authorization", service)
		self.assertIn("expediente NXR Evidence validado", service)
		self.assertIn('doc.channel != "WhatsApp"', service)
		self.assertIn("doc.sender", service)
		self.assertIn("doc.source_message_date", service)
		self.assertIn("doc.external_reference", service)

	def test_stacked_pull_request_is_a_permanent_ci_target(self) -> None:
		for workflow in (
			APP_ROOT.parent / ".github/workflows/nexora-app.yml",
			APP_ROOT.parent / ".github/workflows/nexora-financial.yml",
			APP_ROOT.parent / ".github/workflows/nexora-governance.yml",
		):
			text = workflow.read_text(encoding="utf-8")
			self.assertIn("nexora-reconstruccion", text, workflow)


if __name__ == "__main__":
	unittest.main()
