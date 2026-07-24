from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.purchases.request_service import create_purchase_request, transition_purchase_request


test_dependencies = ["Project", "Cost Center"]


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
	name = frappe.db.get_value("Project", {"project_name": "_Test NEXORA Purchase Project"}, "name")
	if name:
		return str(name)
	return str(
		frappe.get_doc(
			{"doctype": "Project", "project_name": "_Test NEXORA Purchase Project", "status": "Open"}
		)
		.insert(ignore_permissions=True)
		.name
	)


class TestPurchaseRequestMariaDB(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.project = _ensure_project()
		cls.cost_center = frappe.db.get_value("Cost Center", {"is_group": 0}, "name")
		cls.uom = frappe.db.get_value("UOM", {}, "name")
		cls.category = frappe.db.get_value("NXR Economic Category", {"active": 1}, "name")
		if not cls.cost_center or not cls.uom or not cls.category:
			raise AssertionError("Faltan dependencias canónicas para probar solicitudes de compra")
		cls.operator = _ensure_user("nxr-request-operator@example.test", "NEXORA Finance Operator")
		cls.manager = _ensure_user("nxr-request-manager@example.test", "NEXORA Finance Manager")
		cls.viewer = _ensure_user("nxr-request-viewer@example.test", "NEXORA Project Viewer")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _payload(self) -> dict[str, object]:
		return {
			"request_date": "2026-07-24",
			"required_by": "2026-08-10",
			"project": self.project,
			"cost_center": self.cost_center,
			"responsible": self.operator,
			"priority": "High",
			"currency": "HNL",
			"justification": "Materiales y transporte requeridos para el frente de prueba.",
			"lines": [
				{
					"line_code": "MAT-001",
					"item_type": "Goods",
					"description": "Material de construcción",
					"quantity": "3",
					"uom": self.uom,
					"estimated_unit_rate": "250.25",
					"economic_category": self.category,
				},
				{
					"line_code": "SRV-001",
					"item_type": "Service",
					"description": "Transporte de material",
					"quantity": "1",
					"uom": self.uom,
					"estimated_unit_rate": "500",
					"economic_category": self.category,
				},
			],
			"idempotency_key": _key("purchase-request"),
		}

	def test_multiline_request_is_idempotent_approved_and_audited(self) -> None:
		frappe.set_user(self.operator)
		payload = self._payload()
		created = create_purchase_request(payload)
		cached = create_purchase_request(payload)
		self.assertEqual(created, cached)
		self.assertEqual("Draft", created["status"])
		self.assertEqual("1250.75", str(created["total_amount"]))
		self.assertEqual(2, len(created["lines"]))
		review = transition_purchase_request(
			str(created["request"]), "In Review", _key("purchase-review")
		)
		self.assertEqual("In Review", review["status"])
		frappe.set_user(self.manager)
		approved = transition_purchase_request(
			str(created["request"]), "Approved", _key("purchase-approved")
		)
		self.assertEqual("Approved", approved["status"])
		self.assertEqual(self.manager, approved["decided_by"])
		self.assertTrue(
			frappe.db.exists(
				"NXR Audit Event",
				{"reference_doctype": "NXR Purchase Request", "reference_name": created["request"]},
			)
		)

	def test_invalid_quantity_and_unauthorized_approval_are_rejected(self) -> None:
		frappe.set_user(self.operator)
		payload = self._payload()
		payload["lines"][0]["quantity"] = "0"
		with self.assertRaisesRegex(frappe.ValidationError, "cantidad positiva"):
			create_purchase_request(payload)
		valid = self._payload()
		created = create_purchase_request(valid)
		transition_purchase_request(str(created["request"]), "In Review", _key("purchase-review"))
		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			transition_purchase_request(
				str(created["request"]), "Approved", _key("purchase-denied")
			)


if __name__ == "__main__":
	import unittest

	unittest.main()
