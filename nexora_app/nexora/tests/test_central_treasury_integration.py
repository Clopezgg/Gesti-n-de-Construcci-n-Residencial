from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.financial.central_treasury import (
	CENTRAL_REMITTANCE_KEY,
	ensure_central_remittance_account,
)
from nexora.financial.context import service_write


class TestCentralTreasuryMariaDB(FrappeTestCase):
	def setUp(self) -> None:
		super().setUp()
		frappe.set_user("Administrator")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def test_ensure_is_idempotent_and_unique(self) -> None:
		first = ensure_central_remittance_account()
		second = ensure_central_remittance_account()
		self.assertEqual(first, second)
		self.assertEqual(
			1,
			frappe.db.count("NXR Financial Account", {"technical_key": CENTRAL_REMITTANCE_KEY}),
		)
		doc = frappe.get_doc("NXR Financial Account", first)
		self.assertEqual("Treasury", doc.account_role)
		self.assertEqual(1, doc.system_managed)
		self.assertFalse(doc.project)
		self.assertFalse(doc.institution)
		self.assertFalse(doc.account_reference)

	def test_central_account_cannot_be_disabled_or_deleted(self) -> None:
		name = ensure_central_remittance_account()
		doc = frappe.get_doc("NXR Financial Account", name)
		with service_write():
			doc.active = 0
			with self.assertRaises(frappe.ValidationError):
				doc.save(ignore_permissions=True)
		doc.reload()
		with self.assertRaises(frappe.ValidationError):
			doc.delete(ignore_permissions=True)
