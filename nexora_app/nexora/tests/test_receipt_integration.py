from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.file_manager import save_file

from nexora.directory.compliance_service import create_entity_compliance, transition_entity_compliance
from nexora.directory.service import create_entity, transition_entity
from nexora.financial.evidence import register_evidence, review_evidence
from nexora.purchases.order_service import create_order, transition_order
from nexora.purchases.quotation_service import create_quotation, transition_quotation
from nexora.purchases.receipt_service import create_receipt, transition_receipt
from nexora.purchases.request_service import create_purchase_request, transition_purchase_request
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
	name = frappe.db.get_value("Project", {"project_name": "_Test NEXORA Receipt Project"}, "name")
	if name:
		return str(name)
	return str(
		frappe.get_doc(
			{"doctype": "Project", "project_name": "_Test NEXORA Receipt Project", "status": "Open"}
		)
		.insert(ignore_permissions=True)
		.name
	)


class TestReceiptIntegrationMariaDB(FrappeTestCase):
	"""NXR-COM-0010: `receipt_service._received_totals()`/`_update_po_status()` nunca se
	habían ejercido contra Frappe/MariaDB real (solo lógica pura en `test_receipt_core.py`).
	Reproduce el escenario exacto del defecto original: 90 recibido + 30 nuevo sobre una
	línea de 100 con 10% de tolerancia (antes aceptado sin error, ahora rechazado)."""

	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.project = _ensure_project()
		cls.cost_center = frappe.db.get_value("Cost Center", {"is_group": 0}, "name")
		cls.uom = frappe.db.get_value("UOM", {}, "name")
		cls.category = frappe.db.get_value("NXR Economic Category", {"active": 1}, "name")
		if not cls.cost_center or not cls.uom or not cls.category:
			raise AssertionError("Faltan dependencias canónicas para probar recepciones")
		cls.operator = _ensure_user("nxr-receipt-operator@example.test", "NEXORA Finance Operator")
		cls.manager = _ensure_user("nxr-receipt-manager@example.test", "NEXORA Finance Manager")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _evidence(self) -> str:
		frappe.set_user(self.operator)
		file_doc = save_file(
			f"receipt-{uuid.uuid4().hex}.txt", b"NEXORA RECEIPT EVIDENCE", None, None, is_private=1
		)
		registered = register_evidence(
			{
				"project": self.project,
				"evidence_kind": "Other",
				"channel": "Other",
				"file_url": file_doc.file_url,
				"external_reference": f"RECEIPT-{uuid.uuid4().hex[:10]}",
				"idempotency_key": _key("receipt-evidence"),
			}
		)
		frappe.set_user(self.manager)
		review_evidence(str(registered["evidence"]), "Validated", _key("receipt-evidence-review"))
		return str(registered["evidence"])

	def _supplier(self) -> str:
		frappe.set_user(self.operator)
		entity = create_entity(
			{
				"entity_type": "Organization",
				"display_name": f"Proveedor recepción {uuid.uuid4().hex[:8]}",
				"identifiers": [
					{
						"identifier_type": "Internal Code",
						"identifier_value": f"SUP-{uuid.uuid4().hex}",
						"is_primary": 1,
					}
				],
				"idempotency_key": _key("receipt-entity"),
			}
		)
		frappe.set_user(self.manager)
		transition_entity(str(entity["name"]), "Active", _key("receipt-entity-active"))
		compliance = create_entity_compliance(
			{
				"entity": entity["name"],
				"compliance_type": "Supplier",
				"valid_from": "2026-01-01",
				"valid_until": "2027-12-31",
				"evidence": self._evidence(),
				"idempotency_key": _key("receipt-compliance"),
			}
		)
		transition_entity_compliance(
			str(compliance["compliance"]), "Current", _key("receipt-compliance-current")
		)
		supplier = create_supplier_profile(
			{
				"entity": entity["name"],
				"classification": "Goods",
				"valid_from": "2026-01-01",
				"valid_until": "2027-12-31",
				"compliance": compliance["compliance"],
				"idempotency_key": _key("receipt-supplier"),
			}
		)
		transition_supplier_profile(str(supplier["profile"]), "Active", _key("receipt-supplier-active"))
		return str(supplier["profile"])

	def _order(self, supplier: str) -> dict[str, object]:
		frappe.set_user(self.operator)
		request = create_purchase_request(
			{
				"request_date": "2026-07-24",
				"required_by": "2026-08-10",
				"project": self.project,
				"cost_center": self.cost_center,
				"responsible": self.operator,
				"priority": "High",
				"currency": "HNL",
				"justification": "Material para probar recepción acumulada.",
				"lines": [
					{
						"line_code": "MAT-001",
						"item_type": "Goods",
						"description": "Cemento",
						"quantity": "100",
						"uom": self.uom,
						"estimated_unit_rate": "50",
						"economic_category": self.category,
					}
				],
				"idempotency_key": _key("receipt-request"),
			}
		)
		transition_purchase_request(str(request["request"]), "Submitted", _key("receipt-request-submit"))
		transition_purchase_request(str(request["request"]), "In Review", _key("receipt-request-review"))
		frappe.set_user(self.manager)
		transition_purchase_request(str(request["request"]), "Approved", _key("receipt-request-approved"))

		frappe.set_user(self.manager)
		quotation = create_quotation(
			{
				"purchase_request": request["request"],
				"supplier_profile": supplier,
				"currency": "HNL",
				"quotation_date": "2026-07-24",
				"valid_until": "2026-09-30",
				"lines": [
					{
						"line_code": "MAT-001",
						"item_type": "Goods",
						"description": "Cemento",
						"quantity": "100",
						"uom": self.uom,
						"unit_rate": "50",
					}
				],
				"idempotency_key": _key("receipt-quotation"),
			}
		)
		transition_quotation(str(quotation["quotation"]), "Submitted", _key("receipt-quote-submit"))
		transition_quotation(
			str(quotation["quotation"]), "Accepted", _key("receipt-quote-accept"), reason="Única opción"
		)

		frappe.set_user(self.operator)
		order = create_order(
			{
				"purchase_request": request["request"],
				"supplier_quotation": quotation["quotation"],
				"supplier_profile": supplier,
				"currency": "HNL",
				"lines": [
					{
						"line_code": "MAT-001",
						"item_type": "Goods",
						"description": "Cemento",
						"quantity": "100",
						"uom": self.uom,
						"unit_rate": "50",
					}
				],
				"idempotency_key": _key("receipt-order"),
			}
		)
		transition_order(str(order["order"]), "Confirmed", _key("receipt-order-confirmed"))
		frappe.set_user(self.manager)
		transition_order(str(order["order"]), "Approved", _key("receipt-order-approved"))
		transition_order(str(order["order"]), "Sent", _key("receipt-order-sent"))
		return order

	def test_cumulative_over_receipt_beyond_tolerance_is_rejected_and_po_status_reflects_real_totals(
		self,
	) -> None:
		supplier = self._supplier()
		order = self._order(supplier)
		po_line = order["lines"][0]["name"]

		frappe.set_user(self.operator)
		first = create_receipt(
			{
				"purchase_order": order["order"],
				"lines": [
					{
						"purchase_order_line": po_line,
						"quantity": "90",
					}
				],
				"idempotency_key": _key("receipt-first"),
			}
		)
		self.assertEqual("Draft", first["status"])
		transition_receipt(str(first["receipt"]), "Completed", _key("receipt-first-complete"))
		self.assertEqual(
			"Sent",
			frappe.db.get_value("NXR Purchase Order", order["order"], "status"),
			"Con 90 de 100 recibido la orden no debía marcarse completada.",
		)

		with self.assertRaisesRegex(frappe.ValidationError, "excede la tolerancia"):
			create_receipt(
				{
					"purchase_order": order["order"],
					"lines": [
						{
							"purchase_order_line": po_line,
							"quantity": "30",
						}
					],
					"idempotency_key": _key("receipt-second-over"),
				}
			)

		second = create_receipt(
			{
				"purchase_order": order["order"],
				"lines": [
					{
						"purchase_order_line": po_line,
						"quantity": "15",
					}
				],
				"idempotency_key": _key("receipt-second-ok"),
			}
		)
		transition_receipt(str(second["receipt"]), "Completed", _key("receipt-second-complete"))
		self.assertEqual(
			"Completed",
			frappe.db.get_value("NXR Purchase Order", order["order"], "status"),
			"Con 105 de 100 (dentro de tolerancia) la orden debía marcarse completada.",
		)
		self.assertTrue(
			frappe.db.exists(
				"NXR Audit Event",
				{"reference_doctype": "NXR Goods Receipt", "reference_name": second["receipt"]},
			)
		)


if __name__ == "__main__":
	import unittest

	unittest.main()
