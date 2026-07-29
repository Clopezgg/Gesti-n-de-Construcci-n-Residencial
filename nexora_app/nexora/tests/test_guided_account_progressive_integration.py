from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.financial.operational import (
	execute_operational_movement,
	get_financial_account,
	list_financial_accounts,
	preview_operational_movement,
	save_financial_account,
)

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


def _ensure_project(name: str) -> str:
	existing = frappe.db.get_value("Project", {"project_name": name}, "name")
	if existing:
		return str(existing)
	return str(
		frappe.get_doc({"doctype": "Project", "project_name": name, "status": "Open"})
		.insert(ignore_permissions=True)
		.name
	)


class TestGuidedAccountProgressiveMariaDB(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.project = _ensure_project(f"_Test Guided {uuid.uuid4().hex[:8]}")
		cls.other_project = _ensure_project(f"_Test Guided Other {uuid.uuid4().hex[:8]}")
		cls.operator = _ensure_user("nxr-guided-operator@example.test", "NEXORA Finance Operator")
		cls.manager = _ensure_user("nxr-guided-manager@example.test", "NEXORA Finance Manager")
		cls.viewer = _ensure_user("nxr-guided-viewer@example.test", "NEXORA Project Viewer")
		cls.cost_center = frappe.db.get_value("Cost Center", {"is_group": 0}, "name")
		if not cls.cost_center:
			raise AssertionError("Cost Center test dependency did not create a leaf cost center")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _date(self, days: int = -1) -> str:
		return str(frappe.utils.add_days(frappe.utils.today(), days))

	def _income(self, amount: int = 3000) -> dict[str, object]:
		frappe.set_user(self.operator)
		payload = {
			"movement_code": "101",
			"document_date": self._date(-3),
			"project": self.project,
			"account_mode": "Manual",
			"channel": "Cash",
			"currency": "HNL",
			"original_amount": amount,
			"exchange_rate": 1,
			"origin_or_sender": "Fondos de prueba guiada",
			"external_reference": f"INC-{uuid.uuid4().hex[:8]}",
		}
		preview = preview_operational_movement(payload)
		return execute_operational_movement(
			{**payload, "preview_hash": preview["preview_hash"], "idempotency_key": _key("guided-income")}
		)

	def _expense_payload(self, source: str, *, amount: int = 400) -> dict[str, object]:
		return {
			"movement_code": "102",
			"document_date": self._date(-2),
			"project": self.project,
			"economic_category": "CONSTRUCTION_MATERIALS",
			"amount_hnl": amount,
			"currency": "HNL",
			"cost_center": self.cost_center,
			"analytic_splits": [{"cost_center": self.cost_center, "amount_hnl": amount}],
			"beneficiary_doctype": "User",
			"beneficiary": self.operator,
			"payment_method": "Transfer",
			"external_reference": f"PAY-{uuid.uuid4().hex[:8]}",
			"description": "Pago de materiales mediante flujo guiado progresivo",
			"evidence": "/private/files/pago-guiado.pdf",
			"requester": self.operator,
			"approved_by": self.manager,
			"allocations": [{"source": source, "amount_hnl": amount}],
		}

	def test_server_filters_accounts_by_project_direction_currency_channel_and_counterparty(self) -> None:
		frappe.set_user(self.operator)
		origin = save_financial_account(
			{
				"project": self.project,
				"direction": "Origin",
				"account_name": f"Origen {uuid.uuid4().hex[:6]}",
				"origin_or_sender": "Remitente compatible",
				"institution": "Banco Uno",
				"account_reference": "111100001",
				"currency": "USD",
				"default_channel": "Transfer",
			}
		)["account"]
		destination = save_financial_account(
			{
				"project": self.project,
				"direction": "Destination",
				"account_name": f"Destino {uuid.uuid4().hex[:6]}",
				"origin_or_sender": self.operator,
				"institution": "Banco Dos",
				"account_reference": "222200002",
				"currency": "HNL",
				"default_channel": "Transfer",
			}
		)["account"]
		other = save_financial_account(
			{
				"project": self.other_project,
				"direction": "Destination",
				"account_name": f"Otro {uuid.uuid4().hex[:6]}",
				"origin_or_sender": self.operator,
				"institution": "Banco Tres",
				"account_reference": "333300003",
				"currency": "HNL",
				"default_channel": "Transfer",
			}
		)["account"]

		rows = list_financial_accounts(
			self.project,
			direction="Destination",
			currency="HNL",
			channel="Transfer",
			counterparty=self.operator,
		)
		self.assertIn(destination, {row["name"] for row in rows})
		self.assertNotIn(origin, {row["name"] for row in rows})
		self.assertNotIn(other, {row["name"] for row in rows})
		selected = next(row for row in rows if row["name"] == destination)
		self.assertNotEqual("222200002", selected["account_reference"])
		self.assertIn("••••", selected["account_reference"])

		with self.assertRaisesRegex(frappe.ValidationError, "moneda"):
			get_financial_account(
				destination,
				self.project,
				direction="Destination",
				currency="USD",
				channel="Transfer",
				counterparty=self.operator,
			)
		with self.assertRaisesRegex(frappe.PermissionError, "proyecto"):
			get_financial_account(other, self.project, direction="Destination")

	def test_new_destination_account_and_one_time_account_share_expense_engine(self) -> None:
		income = self._income()
		frappe.set_user(self.operator)
		before = frappe.db.count(
			"NXR Financial Account", {"project": self.project, "direction": "Destination"}
		)
		new_payload = {
			**self._expense_payload(str(income["fund_source"])),
			"account_mode": "New",
			"save_financial_account": 1,
			"account_name": f"Pago proveedor {uuid.uuid4().hex[:6]}",
			"institution": "Banco Destino",
			"account_reference": "987654321",
		}
		preview = preview_operational_movement(new_payload)
		self.assertEqual("New", preview["account_mode"])
		result = execute_operational_movement(
			{
				**new_payload,
				"preview_hash": preview["preview_hash"],
				"idempotency_key": _key("guided-expense-new"),
			}
		)
		account = str(result["financial_account"])
		self.assertTrue(account)
		self.assertEqual(
			account,
			frappe.db.get_value(
				"NXR Operation Metadata", {"operation": result["operation"]}, "financial_account"
			),
		)
		self.assertEqual("Destination", frappe.db.get_value("NXR Financial Account", account, "direction"))
		self.assertEqual(
			before + 1,
			frappe.db.count("NXR Financial Account", {"project": self.project, "direction": "Destination"}),
		)

		once_payload = {
			**self._expense_payload(str(income["fund_source"]), amount=250),
			"account_mode": "Manual",
			"save_financial_account": 0,
			"institution": "Banco Temporal",
			"account_reference": "123450000",
		}
		once_preview = preview_operational_movement(once_payload)
		once = execute_operational_movement(
			{
				**once_payload,
				"preview_hash": once_preview["preview_hash"],
				"idempotency_key": _key("guided-expense-once"),
			}
		)
		self.assertIsNone(once["financial_account"])
		self.assertEqual(
			before + 1,
			frappe.db.count("NXR Financial Account", {"project": self.project, "direction": "Destination"}),
		)

	def test_existing_destination_account_rejects_client_manipulation(self) -> None:
		income = self._income()
		frappe.set_user(self.operator)
		account = save_financial_account(
			{
				"project": self.project,
				"direction": "Destination",
				"account_name": f"Proveedor seguro {uuid.uuid4().hex[:6]}",
				"origin_or_sender": self.operator,
				"institution": "Banco Seguro",
				"account_reference": "765432100",
				"currency": "HNL",
				"default_channel": "Transfer",
			}
		)["account"]
		payload = {
			**self._expense_payload(str(income["fund_source"]), amount=300),
			"account_mode": "Existing",
			"financial_account": account,
			"institution": "Banco Manipulado",
			"account_reference": "000000000",
		}
		preview = preview_operational_movement(payload)
		self.assertEqual("Banco Seguro", preview["institution"])
		result = execute_operational_movement(
			{
				**payload,
				"preview_hash": preview["preview_hash"],
				"idempotency_key": _key("guided-expense-existing"),
			}
		)
		self.assertEqual(account, result["financial_account"])

		manipulated = {**payload, "currency": "USD"}
		with self.assertRaisesRegex(frappe.ValidationError, "moneda"):
			preview_operational_movement(manipulated)

	def test_foreign_currency_expense_requires_consistent_conversion(self) -> None:
		income = self._income(amount=5000)
		frappe.set_user(self.operator)
		payload = {
			**self._expense_payload(str(income["fund_source"]), amount=250),
			"account_mode": "Manual",
			"currency": "USD",
			"original_amount": 10,
			"exchange_rate": 25,
			"institution": "Banco Moneda",
			"account_reference": "445566778",
		}
		preview = preview_operational_movement(payload)
		self.assertEqual("250.00", preview["amount_hnl"])
		self.assertEqual("USD", preview["currency"])
		with self.assertRaisesRegex(frappe.ValidationError, "no coincide"):
			preview_operational_movement({**payload, "amount_hnl": 251})

	def test_user_without_financial_permission_cannot_list_or_use_accounts(self) -> None:
		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			list_financial_accounts(self.project, direction="Destination")

	def test_account_save_rolls_back_when_expense_execution_fails(self) -> None:
		income = self._income()
		frappe.set_user(self.operator)
		name = f"Rollback {uuid.uuid4().hex[:8]}"
		payload = {
			**self._expense_payload(str(income["fund_source"]), amount=200),
			"account_mode": "New",
			"save_financial_account": 1,
			"account_name": name,
			"institution": "Banco Rollback",
			"account_reference": "998877665",
		}
		preview = preview_operational_movement(payload)
		frappe.flags.nexora_fail_after_allocation = 1
		try:
			with self.assertRaises(frappe.ValidationError):
				execute_operational_movement(
					{
						**payload,
						"preview_hash": preview["preview_hash"],
						"idempotency_key": _key("guided-rollback"),
					}
				)
		finally:
			frappe.flags.nexora_fail_after_allocation = None
		self.assertFalse(
			frappe.db.exists("NXR Financial Account", {"project": self.project, "account_name": name})
		)


if __name__ == "__main__":
	import unittest

	unittest.main()
