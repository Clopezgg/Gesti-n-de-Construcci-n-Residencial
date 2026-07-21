from __future__ import annotations

import uuid
from datetime import timedelta

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime, today
from frappe.utils.file_manager import save_file

from erpnext.construcontrol.admin_correction_readonly import (
	ensure_derived_expense_fields_are_read_only,
)
from erpnext.construcontrol.admin_correction_setup import ensure_admin_correction_fields
from erpnext.construcontrol.admin_corrections import _token_key
from erpnext.construcontrol.admin_expense_operations import execute_expense_correction
from erpnext.construcontrol.admin_supplier_corrections import (
	execute_supplier_consolidation,
	preview_supplier_consolidation,
)
from erpnext.construcontrol.admin_user_corrections import (
	execute_user_correction,
	preview_user_correction,
)
from erpnext.construcontrol.tests.runtime_smoke import _ensure_test_company
from erpnext.construcontrol.tests.test_mariadb_shared_fixtures import _insert_runtime_doc
from erpnext.construcontrol.tests.test_runtime_user_context import runtime_user


class TestAdministratorCorrectionsMariaDB(FrappeTestCase):
	def setUp(self) -> None:
		frappe.set_user("Administrator")
		ensure_admin_correction_fields()
		ensure_derived_expense_fields_are_read_only()
		self.marker = uuid.uuid4().hex[:12]
		self.company = _ensure_test_company(self.marker)
		self.project = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"Admin Corrections {self.marker}",
				"status": "Open",
				"is_active": "Yes",
				"company": self.company,
			}
		).insert(ignore_permissions=True)
		self.token = f"token-{self.marker}"
		self.authorization_id = f"CCA-TEST-{self.marker.upper()}"
		frappe.cache.set_value(
			_token_key(self.token),
			{
				"session_id": str(frappe.session.sid or ""),
				"authorization_id": self.authorization_id,
				"expires_at": now_datetime() + timedelta(minutes=10),
			},
			expires_in_sec=600,
		)

	def _evidence(self) -> str:
		file_doc = save_file(
			f"admin-correction-{self.marker}.txt",
			b"Evidencia de prueba de correccion administrativa",
			"Project",
			self.project.name,
			is_private=1,
		)
		return str(file_doc.file_url)

	def _supplier(self, name: str) -> str:
		group = frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")
		self.assertTrue(group)
		doc = frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": name,
				"supplier_group": group,
				"supplier_type": "Company",
			}
		).insert(ignore_permissions=True)
		return str(doc.name)

	def _funding(self) -> str:
		doc = _insert_runtime_doc(
			"CC Funding Source",
			{
				"source_id": f"FUND-{self.marker}",
				"source_key": f"runtime:fund:{self.marker}",
				"project": self.project.name,
				"title": f"Fondo {self.marker}",
				"status": "received",
				"reconciliation_status": "reconciled",
				"posting_date": today(),
				"original_currency": "HNL",
				"gross_amount": 1000,
				"fee_amount": 0,
				"treasury_exchange_rate": 1,
				"net_amount_hnl": 1000,
				"amount_hnl": 1000,
			},
		)
		return str(doc.name)

	def _paid_historical_expense(self, supplier: str, funding: str) -> str:
		doc = _insert_runtime_doc(
			"CC Expense Control",
			{
				"source_id": f"EXP-{self.marker}",
				"source_key": f"runtime:expense:{self.marker}",
				"project": self.project.name,
				"title": f"Gasto histórico {self.marker}",
				"posting_date": today(),
				"category": "materials",
				"provider_name": frappe.db.get_value("Supplier", supplier, "supplier_name"),
				"supplier": supplier,
				"funding_source": funding,
				"subtotal_hnl": 500,
				"calculated_total_hnl": 500,
				"amount_hnl": 500,
				"paid_amount_hnl": 500,
				"balance_due_hnl": 0,
				"payment_status": "paid",
				"professional_approval_status": "approved",
				"approval_status": "approved",
				"financial_status": "paid",
				"status": "active",
			},
		)
		return str(doc.name)

	def test_authorized_path_reverses_an_incorrect_imported_payment(self) -> None:
		supplier = self._supplier(f"Proveedor histórico {self.marker}")
		funding = self._funding()
		expense_name = self._paid_historical_expense(supplier, funding)
		expense = frappe.get_doc("CC Expense Control", expense_name)
		expense.paid_amount_hnl = 0
		expense.payment_status = "cancelled"
		with self.assertRaises(frappe.ValidationError):
			expense.save(ignore_permissions=True)

		from erpnext.construcontrol.admin_corrections import preview_expense_correction

		args = {
			"expense_name": expense_name,
			"operation": "reverse_imported_payment",
			"changes": {"paid_amount_hnl": 0, "payment_status": "cancelled"},
			"reason": "El sistema anterior marcó este gasto como pagado por error.",
			"evidence": self._evidence(),
			"authorization_token": self.token,
		}
		preview = preview_expense_correction(**args)
		result = execute_expense_correction(**args, preview_hash=preview["preview_hash"])

		expense.reload()
		self.assertEqual(float(expense.paid_amount_hnl or 0), 0.0)
		self.assertEqual(expense.payment_status, "cancelled")
		self.assertEqual(expense.financial_status, "cancelled")
		self.assertEqual(expense.status, "cancelled")
		self.assertEqual(expense.last_admin_correction_id, self.authorization_id)
		self.assertEqual(result["authorization_id"], self.authorization_id)
		self.assertTrue(
			frappe.db.exists(
				"CC Audit Log",
				{
					"record_type": "CC Expense Control",
					"record_id": expense_name,
					"origin": "ADMIN_CORRECTION",
				},
			)
		)

	def test_supplier_consolidation_reassigns_and_archives_without_deletion(self) -> None:
		canonical = self._supplier(f"Proveedor Oficial {self.marker}")
		duplicate = self._supplier(f"proveedor oficial {self.marker}")
		funding = self._funding()
		expense_name = self._paid_historical_expense(duplicate, funding)
		args = {
			"canonical_supplier": canonical,
			"duplicate_suppliers": [duplicate],
			"reason": "El proveedor duplicado procede de variaciones de nombre en la migración.",
			"evidence": self._evidence(),
			"authorization_token": self.token,
		}
		preview = preview_supplier_consolidation(**args)
		self.assertFalse(preview["blocked"])
		execute_supplier_consolidation(**args, preview_hash=preview["preview_hash"])

		self.assertTrue(frappe.db.exists("Supplier", duplicate))
		self.assertEqual(frappe.db.get_value("Supplier", duplicate, "disabled"), 1)
		self.assertEqual(frappe.db.get_value("Supplier", duplicate, "cc_merged_into"), canonical)
		self.assertEqual(frappe.db.get_value("CC Expense Control", expense_name, "supplier"), canonical)

	def test_user_consolidation_disables_source_and_preserves_the_user_record(self) -> None:
		source = f"source-{self.marker}@example.com"
		target = f"target-{self.marker}@example.com"
		for email, first_name in ((source, "Origen"), (target, "Destino")):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": first_name,
					"enabled": 1,
					"user_type": "System User",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": source,
				"allow": "Project",
				"for_value": self.project.name,
				"is_default": 1,
				"apply_to_all_doctypes": 1,
			}
		).insert(ignore_permissions=True)
		args = {
			"user": source,
			"operation": "consolidate",
			"replacement_user": target,
			"reason": "La cuenta origen está duplicada y debe conservarse solo como historia.",
			"authorization_token": self.token,
		}
		preview = preview_user_correction(**args)
		execute_user_correction(**args, preview_hash=preview["preview_hash"])

		self.assertTrue(frappe.db.exists("User", source))
		self.assertEqual(frappe.db.get_value("User", source, "enabled"), 0)
		self.assertEqual(frappe.db.get_value("User", source, "cc_replacement_user"), target)
		self.assertTrue(
			frappe.db.exists(
				"User Permission",
				{"user": target, "allow": "Project", "for_value": self.project.name},
			)
		)
		self.assertFalse(
			frappe.db.exists(
				"User Permission",
				{"user": source, "allow": "Project", "for_value": self.project.name},
			)
		)

	def test_non_administrator_cannot_read_correction_security(self) -> None:
		user = f"viewer-{self.marker}@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": user,
				"first_name": "Viewer",
				"enabled": 1,
				"user_type": "System User",
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
		from erpnext.construcontrol.admin_correction_security import get_security_status

		with runtime_user(user), self.assertRaises(frappe.PermissionError):
			get_security_status()
