from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.financial.context import service_write

test_dependencies = ["Project", "Cost Center"]

from nexora.financial.operational import (
	execute_operational_movement,
	list_financial_accounts,
	list_operational_ledger,
	preview_operational_movement,
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


def _ensure_project(name: str) -> str:
	existing = frappe.db.get_value("Project", {"project_name": name}, "name")
	if existing:
		return str(existing)
	return str(
		frappe.get_doc({"doctype": "Project", "project_name": name, "status": "Open"})
		.insert(ignore_permissions=True)
		.name
	)


class TestOperationalConsoleMariaDB(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.project = _ensure_project(f"_Test Operational {uuid.uuid4().hex[:8]}")
		cls.operator = _ensure_user("nxr-operational@example.test", "NEXORA Finance Operator")
		cls.manager = _ensure_user("nxr-operational-manager@example.test", "NEXORA Finance Manager")
		cls.auditor = _ensure_user("nxr-operational-auditor@example.test", "NEXORA Auditor")
		cls.cost_center = frappe.db.get_value("Cost Center", {"is_group": 0}, "name")
		if not cls.cost_center:
			raise AssertionError("Cost Center test dependency did not create a leaf cost center")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _date(self, days: int) -> str:
		return str(frappe.utils.add_days(frappe.utils.today(), days))

	def _income_payload(self, *, date: str, amount: int = 1000) -> dict[str, object]:
		return {
			"movement_code": "101",
			"document_date": date,
			"project": self.project,
			"account_mode": "New",
			"channel": "Remittance",
			"currency": "HNL",
			"original_amount": amount,
			"exchange_rate": 1,
			"origin_or_sender": "Karen Vanessa López González",
			"institution": "Banco Atlántida",
			"account_reference": "2020665852",
			"external_reference": f"REF-{uuid.uuid4().hex[:8]}",
			"save_financial_account": 1,
			"account_name": "Cuenta personal Karen",
		}

	def _execute_income(self, *, date: str, amount: int = 1000) -> dict[str, object]:
		frappe.set_user(self.operator)
		payload = self._income_payload(date=date, amount=amount)
		preview = preview_operational_movement(payload)
		return execute_operational_movement(
			{**payload, "preview_hash": preview["preview_hash"], "idempotency_key": _key("op-income")}
		)

	def test_historical_income_uses_document_date_and_reuses_account(self) -> None:
		document_date = self._date(-30)
		first = self._execute_income(date=document_date)
		self.assertEqual(
			document_date, str(frappe.db.get_value("NXR Fund Source", first["fund_source"], "source_date"))
		)
		self.assertEqual(
			document_date, str(frappe.db.get_value("NXR Operation", first["operation"], "operation_date"))
		)
		self.assertEqual(
			"101",
			frappe.db.get_value("NXR Operation Metadata", {"operation": first["operation"]}, "movement_code"),
		)
		accounts = list_financial_accounts(self.project)
		account = next(row for row in accounts if row["account_name"] == "Cuenta personal Karen")
		self.assertEqual("••••65852", account["masked_account_reference"])
		fingerprint = frappe.db.get_value("NXR Financial Account", account["name"], "account_fingerprint")
		self.assertEqual(1, frappe.db.count("NXR Financial Account", {"account_fingerprint": fingerprint}))

		payload = {
			"movement_code": "101",
			"document_date": self._date(-29),
			"project": self.project,
			"account_mode": "Existing",
			"financial_account": account["name"],
			"original_amount": 250,
			"exchange_rate": 1,
			"external_reference": f"REF-{uuid.uuid4().hex[:8]}",
		}
		preview = preview_operational_movement(payload)
		second = execute_operational_movement(
			{**payload, "preview_hash": preview["preview_hash"], "idempotency_key": _key("op-income-reuse")}
		)
		self.assertEqual(
			"Banco Atlántida", frappe.db.get_value("NXR Fund Source", second["fund_source"], "institution")
		)
		self.assertEqual(1, frappe.db.count("NXR Financial Account", {"account_fingerprint": fingerprint}))

	def test_new_mode_ignores_stale_autocomplete_text_and_creates_account(self) -> None:
		frappe.set_user(self.operator)
		payload = {
			**self._income_payload(date=self._date(-8), amount=725),
			"financial_account": "Cuenta escrita que todavía no existe",
			"account_name": f"Cuenta nueva {uuid.uuid4().hex[:8]}",
		}
		preview = preview_operational_movement(payload)
		result = execute_operational_movement(
			{**payload, "preview_hash": preview["preview_hash"], "idempotency_key": _key("op-new-account")}
		)
		self.assertTrue(result["financial_account"])
		self.assertTrue(frappe.db.exists("NXR Financial Account", result["financial_account"]))
		self.assertEqual("New", result["account_mode"])

	def test_existing_mode_rejects_unknown_account_with_actionable_message(self) -> None:
		frappe.set_user(self.operator)
		payload = {
			**self._income_payload(date=self._date(-7), amount=300),
			"account_mode": "Existing",
			"financial_account": "NXR-ACCOUNT-DOES-NOT-EXIST",
			"save_financial_account": 0,
		}
		with self.assertRaisesRegex(
			frappe.ValidationError, "Seleccione una cuenta disponible o use otros datos bancarios"
		):
			preview_operational_movement(payload)

	def test_future_and_closed_period_dates_are_rejected(self) -> None:
		frappe.set_user(self.operator)
		missing_date = self._income_payload(date=self._date(-1))
		missing_date.pop("document_date")
		with self.assertRaisesRegex(frappe.ValidationError, "obligatoria"):
			preview_operational_movement(missing_date)
		with self.assertRaisesRegex(frappe.ValidationError, "futuro"):
			preview_operational_movement(self._income_payload(date=self._date(1)))

		closed_date = self._date(-65)
		month = frappe.utils.getdate(closed_date).strftime("%Y-%m")
		frappe.set_user("Administrator")
		with service_write():
			frappe.get_doc(
				{
					"doctype": "NXR Monthly Close",
					"status": "Approved",
					"project": self.project,
					"close_month": month,
					"close_date": closed_date,
					"total_inflows_hnl": 0,
					"total_outflows_hnl": 0,
				}
			).insert(ignore_permissions=True)
		frappe.set_user(self.operator)
		with self.assertRaisesRegex(frappe.ValidationError, "cerrado"):
			preview_operational_movement(self._income_payload(date=closed_date))

	def test_historical_expense_102_uses_selected_date_and_canonical_allocations(self) -> None:
		income = self._execute_income(date=self._date(-12), amount=1500)
		document_date = self._date(-11)
		payload = {
			"movement_code": "102",
			"document_date": document_date,
			"project": self.project,
			"economic_category": "CONSTRUCTION_MATERIALS",
			"amount_hnl": 400,
			"cost_center": self.cost_center,
			"analytic_splits": [
				{
					"cost_center": self.cost_center,
					"amount_hnl": 400,
				}
			],
			"beneficiary_doctype": "User",
			"beneficiary": self.operator,
			"payment_method": "Transfer",
			"external_reference": f"PAY-{uuid.uuid4().hex[:8]}",
			"description": "Pago de materiales registrado con fecha documental histórica",
			"evidence": "/private/files/pago-materiales.pdf",
			"requester": self.operator,
			"approved_by": self.manager,
			"allocations": [{"source": income["fund_source"], "amount_hnl": 400}],
		}
		frappe.set_user(self.operator)
		preview = preview_operational_movement(payload)
		result = execute_operational_movement(
			{**payload, "preview_hash": preview["preview_hash"], "idempotency_key": _key("op-expense")}
		)
		self.assertEqual(
			document_date, str(frappe.db.get_value("NXR Operation", result["operation"], "operation_date"))
		)
		self.assertEqual(
			"102",
			frappe.db.get_value(
				"NXR Operation Metadata", {"operation": result["operation"]}, "movement_code"
			),
		)
		ledger = list_operational_ledger(self.project, 20)
		row = next(item for item in ledger if item["name"] == result["operation"])
		self.assertEqual(("102", "expense", False), (row["movement_code"], row["tone"], row["struck"]))
		self.assertEqual(self.operator, row["counterparty"])

	def test_income_annulment_preserves_original_and_uses_selected_date(self) -> None:
		original_date = self._date(-20)
		income = self._execute_income(date=original_date)
		frappe.set_user(self.manager)
		other_project = _ensure_project(f"_Test Other Operational {uuid.uuid4().hex[:8]}")
		with self.assertRaisesRegex(frappe.ValidationError, "proyecto del documento original"):
			preview_operational_movement(
				{
					"movement_code": "303",
					"document_date": self._date(-19),
					"project": other_project,
					"reference_name": income["operation"],
					"description": "Anulación por referencia incorrecta",
				}
			)
		with self.assertRaisesRegex(frappe.ValidationError, "anterior"):
			preview_operational_movement(
				{
					"movement_code": "303",
					"document_date": self._date(-21),
					"project": self.project,
					"reference_name": income["operation"],
					"description": "Anulación por referencia incorrecta",
				}
			)
		payload = {
			"movement_code": "303",
			"document_date": self._date(-19),
			"project": self.project,
			"reference_name": income["operation"],
			"description": "Anulación por referencia incorrecta",
		}
		preview = preview_operational_movement(payload)
		result = execute_operational_movement(
			{**payload, "preview_hash": preview["preview_hash"], "idempotency_key": _key("op-cancel")}
		)
		self.assertTrue(frappe.db.exists("NXR Operation", income["operation"]))
		self.assertEqual(
			self._date(-19), str(frappe.db.get_value("NXR Operation", result["operation"], "operation_date"))
		)
		self.assertEqual(
			"303",
			frappe.db.get_value(
				"NXR Operation Metadata", {"operation": result["operation"]}, "movement_code"
			),
		)
		ledger = list_operational_ledger(self.project, 20)
		cancelled = next(row for row in ledger if row["name"] == result["operation"])
		self.assertEqual(
			("voided", True, "Contabilizado"), (cancelled["tone"], cancelled["struck"], cancelled["status"])
		)
