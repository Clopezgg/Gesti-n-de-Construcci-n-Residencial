from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.financial.corrections import (
	execute_operation_correction,
	get_operation_for_correction,
	preview_operation_correction,
)
from nexora.financial.operations import execute_financial_operation
from nexora.financial.sources import create_fund_source


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
	elif not frappe.db.exists("Has Role", {"parent": email, "role": role}):
		user = frappe.get_doc("User", email)
		user.append("roles", {"role": role})
		user.save(ignore_permissions=True)
	return email


def _ensure_project(project_name: str) -> str:
	existing = frappe.db.get_value("Project", {"project_name": project_name}, "name")
	if existing:
		return str(existing)
	return str(
		frappe.get_doc({"doctype": "Project", "project_name": project_name, "status": "Open"})
		.insert(ignore_permissions=True)
		.name
	)


class TestGuidedOperationCorrection(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.project = _ensure_project("_Test Guided Correction")
		cls.operator = _ensure_user(
			"nxr-correction-operator@example.test",
			"NEXORA Finance Operator",
		)
		cls.manager = _ensure_user(
			"nxr-correction-manager@example.test",
			"NEXORA Finance Manager",
		)

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _source(self, amount: int = 1000) -> dict:
		frappe.set_user(self.operator)
		return create_fund_source(
			{
				"idempotency_key": _key("guided-source"),
				"source_name": f"Remesa guiada {uuid.uuid4().hex[:8]}",
				"channel": "Cash",
				"project": self.project,
				"currency": "HNL",
				"original_amount": amount,
				"exchange_rate": 1,
				"origin_or_sender": "Remitente original",
				"custodian": self.operator,
			}
		)

	def _payload(self, document_number: str) -> dict:
		frappe.set_user(self.manager)
		row = get_operation_for_correction(document_number)
		return {
			"document": document_number,
			"document_date": row["document_date"],
			"source_name": row["source_name"],
			"channel": row["channel"],
			"currency": row["currency"],
			"original_amount": row["original_amount"],
			"exchange_rate": row["exchange_rate"],
			"origin_or_sender": row["origin_or_sender"],
			"institution": row["institution"],
			"account_reference": row["account_reference"],
			"external_reference": row["external_reference"],
			"evidence": row["evidence"],
			"reason": "Corrección guiada validada por integración.",
		}

	def test_date_and_remittance_data_correction_requires_no_evidence(self) -> None:
		created = self._source()
		payload = self._payload(created["document_number"])
		payload["document_date"] = frappe.utils.add_days(frappe.utils.today(), -1)
		payload["source_name"] = "Remesa corregida"
		payload["origin_or_sender"] = "Remitente corregido"
		payload["evidence"] = ""
		preview = preview_operation_correction(payload)
		self.assertFalse(preview["evidence_required"])
		self.assertIn("document_date", preview["changed_fields"])
		self.assertIn("source_name", preview["changed_fields"])
		key = _key("guided-correction")
		request = {**payload, "preview_hash": preview["preview_hash"], "idempotency_key": key}
		result = execute_operation_correction(request)
		self.assertEqual(
			payload["document_date"],
			str(frappe.db.get_value("NXR Operation", created["operation"], "operation_date")),
		)
		self.assertEqual(
			"Remesa corregida",
			frappe.db.get_value("NXR Fund Source", created["fund_source"], "source_name"),
		)
		self.assertEqual(
			"Remitente corregido",
			frappe.db.get_value("NXR Fund Source", created["fund_source"], "origin_or_sender"),
		)
		self.assertEqual(
			"DOCUMENT_SUBSTITUTION",
			frappe.db.get_value("NXR Operation", result["correction_operation"], "operation_code"),
		)
		self.assertEqual(
			"304",
			frappe.db.get_value(
				"NXR Operation Metadata",
				{"operation": result["correction_operation"]},
				"movement_code",
			),
		)
		self.assertTrue(
			frappe.db.exists(
				"NXR Audit Event",
				{
					"event_type": "operation_document_corrected",
					"reference_name": created["operation"],
				},
			)
		)
		self.assertEqual(result, execute_operation_correction(request))

	def test_pristine_income_amount_can_be_corrected_atomically(self) -> None:
		created = self._source(1000)
		payload = self._payload(created["document_number"])
		payload["original_amount"] = 1200
		preview = preview_operation_correction(payload)
		self.assertTrue(preview["amount_editable"])
		self.assertEqual("200.00", preview["financial_delta_hnl"])
		execute_operation_correction(
			{
				**payload,
				"preview_hash": preview["preview_hash"],
				"idempotency_key": _key("guided-amount"),
			}
		)
		self.assertEqual(
			1200,
			frappe.db.get_value("NXR Fund Source", created["fund_source"], "amount_hnl"),
		)
		self.assertEqual(
			1200,
			frappe.db.get_value("NXR Operation", created["operation"], "amount_hnl"),
		)
		self.assertEqual(
			1200,
			frappe.db.get_value(
				"NXR Operation Effect",
				{"operation": created["operation"], "effect_type": "Received"},
				"amount_hnl",
			),
		)

	def test_used_income_rejects_amount_change_but_keeps_metadata_available(self) -> None:
		created = self._source(1000)
		frappe.set_user(self.operator)
		execute_financial_operation(
			{
				"idempotency_key": _key("guided-spend"),
				"operation_type": "Outflow",
				"project": self.project,
				"amount_hnl": 100,
				"allocations": [{"source": created["fund_source"], "amount_hnl": 100}],
				"requester": self.operator,
				"approved_by": self.manager,
			}
		)
		payload = self._payload(created["document_number"])
		payload["original_amount"] = 1100
		with self.assertRaisesRegex(frappe.ValidationError, "importe y la tasa están bloqueados"):
			preview_operation_correction(payload)
		payload["original_amount"] = 1000
		payload["source_name"] = "Nombre corregido sin mover saldo"
		preview = preview_operation_correction(payload)
		self.assertFalse(preview["amount_editable"])
		self.assertIn("source_name", preview["changed_fields"])

	def test_operator_cannot_apply_manager_only_correction(self) -> None:
		created = self._source()
		frappe.set_user(self.operator)
		with self.assertRaises(frappe.PermissionError):
			get_operation_for_correction(created["document_number"])
