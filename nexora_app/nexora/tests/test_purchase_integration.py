from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.file_manager import save_file

from nexora.directory.compliance_service import (
	create_entity_compliance,
	transition_entity_compliance,
)
from nexora.directory.service import create_entity, transition_entity
from nexora.financial.evidence import register_evidence, review_evidence
from nexora.purchases.service import (
	create_supplier_profile,
	get_supplier_profile,
	transition_supplier_profile,
)


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
	name = frappe.db.get_value("Project", {"project_name": "_Test NEXORA Supplier Project"}, "name")
	if name:
		return str(name)
	return str(
		frappe.get_doc(
			{"doctype": "Project", "project_name": "_Test NEXORA Supplier Project", "status": "Open"}
		)
		.insert(ignore_permissions=True)
		.name
	)


class TestPurchaseSupplierMariaDB(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.project = _ensure_project()
		cls.operator = _ensure_user("nxr-supplier-operator@example.test", "NEXORA Finance Operator")
		cls.manager = _ensure_user("nxr-supplier-manager@example.test", "NEXORA Finance Manager")
		cls.viewer = _ensure_user("nxr-supplier-viewer@example.test", "NEXORA Project Viewer")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _evidence(self) -> str:
		frappe.set_user(self.operator)
		file_doc = save_file(
			f"supplier-{uuid.uuid4().hex}.txt",
			b"NEXORA SUPPLIER COMPLIANCE",
			None,
			None,
			is_private=1,
		)
		registered = register_evidence(
			{
				"project": self.project,
				"evidence_kind": "Other",
				"channel": "Other",
				"file_url": file_doc.file_url,
				"external_reference": f"SUPPLIER-{uuid.uuid4().hex[:10]}",
				"idempotency_key": _key("supplier-evidence"),
			}
		)
		frappe.set_user(self.manager)
		review_evidence(str(registered["evidence"]), "Validated", _key("supplier-evidence-review"))
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
				"idempotency_key": _key("supplier-entity"),
			}
		)
		frappe.set_user(self.manager)
		transition_entity(str(created["name"]), "Active", _key("supplier-entity-active"))
		return str(created["name"])

	def _compliance(self, entity: str, compliance_type: str = "Supplier") -> str:
		frappe.set_user(self.manager)
		created = create_entity_compliance(
			{
				"entity": entity,
				"compliance_type": compliance_type,
				"valid_from": "2026-01-01",
				"valid_until": "2027-12-31",
				"evidence": self._evidence(),
				"idempotency_key": _key("supplier-compliance"),
			}
		)
		frappe.set_user(self.manager)
		transition_entity_compliance(
			str(created["compliance"]),
			"Current",
			_key("supplier-compliance-current"),
		)
		return str(created["compliance"])

	def test_supplier_profile_uses_entity_role_compliance_and_audit(self) -> None:
		entity = self._entity()
		compliance = self._compliance(entity)
		key = _key("supplier-profile")
		payload = {
			"entity": entity,
			"classification": "Goods",
			"valid_from": "2026-01-01",
			"valid_until": "2027-12-31",
			"compliance": compliance,
			"idempotency_key": key,
		}
		frappe.set_user(self.manager)
		created = create_supplier_profile(payload)
		cached = create_supplier_profile(payload)
		self.assertEqual(created, cached)
		self.assertEqual("Draft", created["status"])
		self.assertEqual(
			"Supplier", frappe.db.get_value("NXR Entity Role", created["entity_role"], "role_type")
		)
		activated = transition_supplier_profile(
			str(created["profile"]), "Active", _key("supplier-profile-active")
		)
		self.assertEqual("Active", activated["status"])
		self.assertEqual("Current", activated["compliance_status"])
		detail = get_supplier_profile(str(created["profile"]))
		self.assertEqual(entity, detail["canonical_entity"])
		self.assertTrue(
			frappe.db.exists(
				"NXR Audit Event",
				{"reference_doctype": "NXR Supplier Profile", "reference_name": created["profile"]},
			)
		)
		with self.assertRaisesRegex(frappe.ValidationError, "superpuesto"):
			create_supplier_profile({**payload, "idempotency_key": _key("supplier-overlap")})

	def test_wrong_compliance_and_viewer_write_are_rejected(self) -> None:
		entity = self._entity()
		identity_compliance = self._compliance(entity, "Identity")
		frappe.set_user(self.manager)
		with self.assertRaisesRegex(frappe.ValidationError, "Supplier"):
			create_supplier_profile(
				{
					"entity": entity,
					"classification": "Services",
					"valid_from": "2026-01-01",
					"valid_until": "2027-12-31",
					"compliance": identity_compliance,
					"idempotency_key": _key("supplier-wrong-compliance"),
				}
			)
		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			create_supplier_profile(
				{
					"entity": entity,
					"classification": "Services",
					"valid_from": "2026-01-01",
					"idempotency_key": _key("supplier-denied"),
				}
			)


if __name__ == "__main__":
	import unittest

	unittest.main()
