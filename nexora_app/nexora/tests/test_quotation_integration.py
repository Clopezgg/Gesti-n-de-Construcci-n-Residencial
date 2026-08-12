from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.file_manager import save_file

from nexora.directory.compliance_service import create_entity_compliance, transition_entity_compliance
from nexora.directory.service import create_entity, transition_entity
from nexora.financial.evidence import register_evidence, review_evidence
from nexora.purchases.quotation_service import (
	compare_quotations,
	create_quotation,
	get_quotation,
	list_quotations,
	transition_quotation,
)
from nexora.purchases.request_service import create_purchase_request
from nexora.purchases.service import create_supplier_profile, transition_supplier_profile


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


def _ensure_project() -> str:
	name = frappe.db.get_value("Project", {"project_name": "_Test NEXORA Quotation Project"}, "name")
	if name:
		return str(name)
	return str(
		frappe.get_doc(
			{"doctype": "Project", "project_name": "_Test NEXORA Quotation Project", "status": "Open"}
		)
		.insert(ignore_permissions=True)
		.name
	)


class TestQuotationMariaDB(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.project = _ensure_project()
		cls.cost_center = frappe.db.get_value("Cost Center", {"is_group": 0}, "name")
		cls.uom = frappe.db.get_value("UOM", {}, "name")
		cls.category = frappe.db.get_value("NXR Economic Category", {"active": 1}, "name")
		if not cls.cost_center or not cls.uom or not cls.category:
			raise AssertionError("Faltan dependencias canónicas para probar cotizaciones")
		cls.operator = _ensure_user("nxr-quote-operator@example.test", "NEXORA Finance Operator")
		cls.manager = _ensure_user("nxr-quote-manager@example.test", "NEXORA Finance Manager")
		cls.viewer = _ensure_user("nxr-quote-viewer@example.test", "NEXORA Project Viewer")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _evidence(self) -> str:
		frappe.set_user(self.operator)
		file_doc = save_file(
			f"quote-{uuid.uuid4().hex}.txt", b"NEXORA QUOTATION EVIDENCE", None, None, is_private=1
		)
		registered = register_evidence(
			{
				"project": self.project,
				"evidence_kind": "Other",
				"channel": "Other",
				"file_url": file_doc.file_url,
				"external_reference": f"QUOTE-{uuid.uuid4().hex[:10]}",
				"idempotency_key": _key("quote-evidence"),
			}
		)
		frappe.set_user(self.manager)
		review_evidence(str(registered["evidence"]), "Validated", _key("quote-evidence-review"))
		return str(registered["evidence"])

	def _entity(self) -> str:
		frappe.set_user(self.operator)
		created = create_entity(
			{
				"entity_type": "Organization",
				"display_name": f"Proveedor {uuid.uuid4().hex[:8]}",
				"identifiers": [
					{
						"identifier_type": "Internal Code",
						"identifier_value": f"SUP-{uuid.uuid4().hex}",
						"is_primary": 1,
					}
				],
				"idempotency_key": _key("quote-entity"),
			}
		)
		frappe.set_user(self.manager)
		transition_entity(str(created["name"]), "Active", _key("quote-entity-active"))
		return str(created["name"])

	def _compliance(self, entity: str) -> str:
		frappe.set_user(self.manager)
		created = create_entity_compliance(
			{
				"entity": entity,
				"compliance_type": "Supplier",
				"valid_from": "2026-01-01",
				"valid_until": "2027-12-31",
				"evidence": self._evidence(),
				"idempotency_key": _key("quote-compliance"),
			}
		)
		transition_entity_compliance(str(created["compliance"]), "Current", _key("quote-compliance-current"))
		return str(created["compliance"])

	def _supplier(self, entity: str, compliance: str) -> str:
		frappe.set_user(self.manager)
		created = create_supplier_profile(
			{
				"entity": entity,
				"classification": "Goods",
				"valid_from": "2026-01-01",
				"valid_until": "2027-12-31",
				"compliance": compliance,
				"idempotency_key": _key("quote-supplier"),
			}
		)
		transition_supplier_profile(str(created["profile"]), "Active", _key("quote-supplier-active"))
		return str(created["profile"])

	def _purchase_request(self) -> str:
		frappe.set_user(self.operator)
		created = create_purchase_request(
			{
				"request_date": "2026-07-24",
				"required_by": "2026-08-10",
				"project": self.project,
				"cost_center": self.cost_center,
				"responsible": self.operator,
				"priority": "High",
				"currency": "HNL",
				"justification": "Materiales para prueba de cotización.",
				"lines": [
					{
						"line_code": "MAT-001",
						"item_type": "Goods",
						"description": "Material de construcción",
						"quantity": "5",
						"uom": self.uom,
						"estimated_unit_rate": "100",
						"economic_category": self.category,
					}
				],
				"idempotency_key": _key("quote-purchase-request"),
			}
		)
		return str(created["request"])

	def test_quotation_lifecycle_is_idempotent_and_audited(self) -> None:
		entity = self._entity()
		compliance = self._compliance(entity)
		supplier = self._supplier(entity, compliance)
		purchase_request = self._purchase_request()

		frappe.set_user(self.manager)
		key = _key("quotation")
		payload = {
			"purchase_request": purchase_request,
			"supplier_profile": supplier,
			"currency": "HNL",
			"quotation_date": "2026-07-24",
			"valid_until": "2026-09-30",
			"payment_terms": "50% anticipo, 50% contra entrega",
			"lines": [
				{
					"line_code": "001",
					"item_type": "Goods",
					"description": "Material cotizado",
					"quantity": "5",
					"uom": self.uom,
					"unit_rate": "95.00",
				}
			],
			"idempotency_key": key,
		}
		created = create_quotation(payload)
		cached = create_quotation(payload)
		self.assertEqual(created, cached)

		conflicting_payload = {**payload, "payment_terms": "Pago completo contra entrega"}
		with self.assertRaises(frappe.ValidationError):
			create_quotation(conflicting_payload)

		self.assertEqual("Draft", created["status"])
		self.assertEqual("475.00", str(created["total_amount"]))
		self.assertEqual(entity, created["supplier_entity"])

		submitted = transition_quotation(str(created["quotation"]), "Submitted", _key("quote-submit"))
		self.assertEqual("Submitted", submitted["status"])

		accepted = transition_quotation(
			str(created["quotation"]), "Accepted", _key("quote-accept"), reason="Mejor precio y condiciones"
		)
		self.assertEqual("Accepted", accepted["status"])
		self.assertEqual(1, accepted["selected"])
		self.assertEqual(self.manager, accepted["selected_by"])

		self.assertTrue(
			frappe.db.exists(
				"NXR Audit Event",
				{"reference_doctype": "NXR Supplier Quotation", "reference_name": created["quotation"]},
			)
		)

		listed = list_quotations(purchase_request=purchase_request)
		self.assertGreaterEqual(len(listed), 1)

		compared = compare_quotations(purchase_request)
		self.assertEqual(1, len(compared))
		self.assertEqual("Accepted", compared[0]["status"])

	def test_multiple_quotations_and_selection_excludes_others(self) -> None:
		entity = self._entity()
		compliance = self._compliance(entity)
		supplier = self._supplier(entity, compliance)
		pr = self._purchase_request()

		frappe.set_user(self.manager)
		q1 = create_quotation(
			{
				"purchase_request": pr,
				"supplier_profile": supplier,
				"currency": "HNL",
				"valid_until": "2026-09-30",
				"lines": [
					{
						"line_code": "001",
						"description": "Opción A",
						"quantity": "1",
						"uom": self.uom,
						"unit_rate": "100",
					}
				],
				"idempotency_key": _key("quote-a"),
			}
		)
		q2 = create_quotation(
			{
				"purchase_request": pr,
				"supplier_profile": supplier,
				"currency": "HNL",
				"valid_until": "2026-09-30",
				"lines": [
					{
						"line_code": "001",
						"description": "Opción B",
						"quantity": "1",
						"uom": self.uom,
						"unit_rate": "90",
					}
				],
				"idempotency_key": _key("quote-b"),
			}
		)
		transition_quotation(str(q1["quotation"]), "Submitted", _key("quote-a-submit"))
		transition_quotation(str(q2["quotation"]), "Submitted", _key("quote-b-submit"))
		transition_quotation(str(q1["quotation"]), "Accepted", _key("quote-a-accept"), reason="Mejor calidad")

		q1_detail = get_quotation(str(q1["quotation"]))
		q2_detail = get_quotation(str(q2["quotation"]))
		self.assertEqual(1, q1_detail["selected"])
		self.assertEqual(0, q2_detail["selected"])

		# Aceptar una segunda cotización sobre la misma solicitud ejercita de verdad
		# `_deselect_other_quotations` (la primera aceptación no tenía nada que
		# deseleccionar). Debe deseleccionar q1 sin lanzar error de escritura.
		transition_quotation(
			str(q2["quotation"]), "Accepted", _key("quote-b-accept"), reason="Precio final mejor"
		)
		q1_after = get_quotation(str(q1["quotation"]))
		q2_after = get_quotation(str(q2["quotation"]))
		self.assertEqual(0, q1_after["selected"])
		self.assertEqual(1, q2_after["selected"])

	def test_invalid_supplier_and_missing_lines_rejected(self) -> None:
		entity = self._entity()
		compliance = self._compliance(entity)
		supplier = self._supplier(entity, compliance)
		pr = self._purchase_request()

		frappe.set_user(self.manager)
		with self.assertRaises(frappe.ValidationError):
			create_quotation(
				{
					"purchase_request": pr,
					"supplier_profile": supplier,
					"currency": "HNL",
					"valid_until": "2026-09-30",
					"lines": [],
					"idempotency_key": _key("quote-no-lines"),
				}
			)

		with self.assertRaises(frappe.ValidationError):
			create_quotation(
				{
					"purchase_request": pr,
					"supplier_profile": "nonexistent",
					"currency": "HNL",
					"valid_until": "2026-09-30",
					"lines": [
						{
							"line_code": "001",
							"description": "Test",
							"quantity": "1",
							"uom": self.uom,
							"unit_rate": "100",
						}
					],
					"idempotency_key": _key("quote-bad-supplier"),
				}
			)

		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			create_quotation(
				{
					"purchase_request": pr,
					"supplier_profile": supplier,
					"currency": "HNL",
					"valid_until": "2026-09-30",
					"lines": [
						{
							"line_code": "001",
							"description": "Test",
							"quantity": "1",
							"uom": self.uom,
							"unit_rate": "100",
						}
					],
					"idempotency_key": _key("quote-denied"),
				}
			)

	def test_get_list_and_compare_quotations_reject_a_viewer_without_an_explicit_project_grant(
		self,
	) -> None:
		"""NXR-SEC-0001 (Bloque 19): regresión real — `get_quotation`/
		`list_quotations`/`compare_quotations` deben resolver el permiso contra el
		proyecto real del documento, no bastar con el rol amplio "NEXORA Project
		Viewer"."""
		entity = self._entity()
		compliance = self._compliance(entity)
		supplier = self._supplier(entity, compliance)
		purchase_request = self._purchase_request()
		frappe.set_user(self.manager)
		created = create_quotation(
			{
				"purchase_request": purchase_request,
				"supplier_profile": supplier,
				"currency": "HNL",
				"quotation_date": "2026-07-24",
				"valid_until": "2026-09-30",
				"lines": [
					{
						"line_code": "001",
						"item_type": "Goods",
						"description": "Material cotizado",
						"quantity": "1",
						"uom": self.uom,
						"unit_rate": "10.00",
					}
				],
				"idempotency_key": _key("quote-scoping"),
			}
		)
		quotation = str(created["quotation"])
		transition_quotation(quotation, "Submitted", _key("quote-scoping-submit"))

		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			get_quotation(quotation)
		with self.assertRaises(frappe.PermissionError):
			list_quotations(purchase_request=purchase_request)
		with self.assertRaises(frappe.PermissionError):
			compare_quotations(purchase_request)

		frappe.set_user("Administrator")
		grant = frappe.get_doc(
			{"doctype": "User Permission", "user": self.viewer, "allow": "Project", "for_value": self.project}
		).insert(ignore_permissions=True)
		try:
			frappe.set_user(self.viewer)
			snapshot = get_quotation(quotation)
			self.assertEqual(quotation, snapshot["quotation"])
			rows = list_quotations(purchase_request=purchase_request)
			self.assertTrue(any(row["quotation"] == quotation for row in rows))
			compared = compare_quotations(purchase_request)
			self.assertTrue(any(row["quotation"] == quotation for row in compared))
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("User Permission", grant.name, ignore_permissions=True)


if __name__ == "__main__":
	import unittest

	unittest.main()
