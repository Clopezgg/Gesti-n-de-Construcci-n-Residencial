from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.file_manager import save_file

from nexora.financial.analytics import prepare_central_payload
from nexora.financial.context import service_write
from nexora.financial.db import issue_document_number, link_sequence
from nexora.financial.evidence import register_evidence, review_evidence


def _key(prefix: str) -> str:
	return f"{prefix}-{uuid.uuid4().hex}"


def _ensure_user(email: str, role: str) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@", 1)[0],
				"enabled": 1,
				"send_welcome_email": 0,
				"roles": [{"role": role}],
			}
		).insert(ignore_permissions=True)
	return email


def _ensure_project() -> str:
	name = frappe.db.get_value("Project", {"project_name": "_Test Evidence Project"}, "name")
	if name:
		return str(name)
	return str(
		frappe.get_doc({"doctype": "Project", "project_name": "_Test Evidence Project", "status": "Open"})
		.insert(ignore_permissions=True)
		.name
	)


class TestEvidenceMariaDB(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.project = _ensure_project()
		cls.operator = _ensure_user("nxr-evidence-operator@example.test", "NEXORA Finance Operator")
		cls.manager = _ensure_user("nxr-evidence-manager@example.test", "NEXORA Finance Manager")
		cls.viewer = _ensure_user("nxr-evidence-viewer@example.test", "NEXORA Project Viewer")
		cls.cost_center = frappe.db.get_value("Cost Center", {"is_group": 0}, "name")
		if not cls.cost_center:
			raise AssertionError("Cost Center test dependency did not create a leaf cost center")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _private_file(self, name: str, content: bytes) -> str:
		file_doc = save_file(name, content, "Project", self.project, is_private=1)
		self.assertTrue(file_doc.is_private)
		self.assertTrue(str(file_doc.file_url).startswith("/private/files/"))
		return str(file_doc.file_url)

	def _register_whatsapp(self, suffix: str = "one") -> dict[str, object]:
		frappe.set_user(self.operator)
		return register_evidence(
			{
				"project": self.project,
				"evidence_kind": "External Authorization",
				"channel": "WhatsApp",
				"file_url": self._private_file(
					f"whatsapp-authorization-{suffix}-{uuid.uuid4().hex}.txt",
					f"Autorización NEXORA {suffix}".encode(),
				),
				"source_message_date": "2026-07-23 10:30:00",
				"sender": "Autorizador de prueba",
				"external_reference": f"WA-{suffix}-{uuid.uuid4().hex[:8]}",
				"notes": "Evidencia demostrativa aislada.",
				"idempotency_key": _key("evidence-register"),
			}
		)

	def test_registration_review_permissions_and_idempotency(self) -> None:
		frappe.set_user(self.operator)
		file_url = self._private_file(
			f"payment-{uuid.uuid4().hex}.txt", b"NEXORA PAYMENT PROOF"
		)
		key = _key("evidence-idempotent")
		payload = {
			"project": self.project,
			"evidence_kind": "Payment Proof",
			"channel": "Bank Receipt",
			"file_url": file_url,
			"external_reference": "BANK-001",
			"idempotency_key": key,
		}
		first = register_evidence(payload)
		self.assertEqual(first, register_evidence(payload))
		self.assertEqual(64, len(str(first["content_sha256"])))
		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			review_evidence(str(first["evidence"]), "Validated", _key("review-denied"))
		frappe.set_user(self.manager)
		reviewed = review_evidence(
			str(first["evidence"]), "Validated", _key("review-allowed"), "Comprobante revisado."
		)
		self.assertEqual("Validated", reviewed["status"])
		self.assertTrue(
			frappe.db.exists(
				"NXR Audit Event", {"reference_doctype": "NXR Evidence", "reference_name": first["evidence"]}
			)
		)

	def test_special_operation_requires_validated_whatsapp_record(self) -> None:
		registered = self._register_whatsapp("special")
		base = {
			"operation_code": "DONATION_PAYMENT",
			"economic_category": "DONATION",
			"project": self.project,
			"amount_hnl": 100,
			"cost_center": self.cost_center,
			"beneficiary_doctype": "User",
			"beneficiary": self.viewer,
			"approved_by": self.manager,
			"payment_method": "Cash",
			"external_reference": "DONATION-001",
			"operation_date": "2026-07-23",
		}
		frappe.set_user(self.operator)
		with self.assertRaisesRegex(frappe.ValidationError, "validada"):
			prepare_central_payload({**base, "evidence": registered["evidence"]})
		frappe.set_user(self.manager)
		review_evidence(str(registered["evidence"]), "Validated", _key("special-review"))
		frappe.set_user(self.operator)
		prepared = prepare_central_payload({**base, "evidence": registered["evidence"]})
		self.assertTrue(str(prepared["evidence"]).startswith("/private/files/"))
		with self.assertRaisesRegex(frappe.ValidationError, "expediente NXR Evidence"):
			prepare_central_payload({**base, "evidence": "/private/files/unregistered.txt"})

	def test_superseding_preserves_original_and_increments_version(self) -> None:
		first = self._register_whatsapp("original")
		frappe.set_user(self.manager)
		review_evidence(str(first["evidence"]), "Rejected", _key("reject-original"))
		frappe.set_user(self.operator)
		second = register_evidence(
			{
				"project": self.project,
				"evidence_kind": "External Authorization",
				"channel": "WhatsApp",
				"file_url": self._private_file(
					f"whatsapp-replacement-{uuid.uuid4().hex}.txt",
					"Autorización NEXORA corregida".encode(),
				),
				"source_message_date": "2026-07-23 11:00:00",
				"sender": "Autorizador de prueba",
				"external_reference": "WA-REPLACEMENT",
				"supersedes": first["evidence"],
				"idempotency_key": _key("replace-evidence"),
			}
		)
		self.assertEqual(2, second["version"])
		self.assertEqual("Superseded", frappe.db.get_value("NXR Evidence", first["evidence"], "status"))
		self.assertTrue(frappe.db.exists("NXR Evidence", first["evidence"]))

	def test_executed_operation_rejects_edit_and_delete(self) -> None:
		frappe.set_user(self.operator)
		key = _key("immutable-operation")
		number, sequence = issue_document_number("NXR Operation", key)
		with service_write():
			doc = frappe.get_doc(
				{
					"doctype": "NXR Operation",
					"document_number": number,
					"operation_code": "MAXIMUM_ACCOUNT",
					"operation_type": "Outflow",
					"status": "Executed",
					"project": self.project,
					"operation_date": "2026-07-23",
					"currency": "HNL",
					"amount": 10,
					"exchange_rate": 1,
					"idempotency_key": key,
					"payload_hash": "a" * 64,
					"preview_hash": "b" * 64,
					"executed_by": self.operator,
					"correlation_id": uuid.uuid4().hex,
				}
			).insert(ignore_permissions=True)
		link_sequence(sequence, doc.name)
		doc.amount = 11
		with self.assertRaisesRegex(frappe.ValidationError, "inmutable"):
			with service_write():
				doc.save(ignore_permissions=True)
		doc.reload()
		with self.assertRaisesRegex(frappe.ValidationError, "documento compensatorio"):
			doc.delete(ignore_permissions=True)


if __name__ == "__main__":
	import unittest

	unittest.main()
