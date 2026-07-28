from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.financial.sources import cancel_fund_source, create_fund_source, list_source_balances


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


class TestFundSelectorMariaDB(FrappeTestCase):
	def setUp(self) -> None:
		super().setUp()
		frappe.set_user("Administrator")
		marker = uuid.uuid4().hex[:10]
		self.project = self._project(f"_Test NEXORA Fund Selector {marker}")
		self.other_project = self._project(f"_Test NEXORA Fund Selector Other {marker}")
		self.empty_project = self._project(f"_Test NEXORA Fund Selector Empty {marker}")
		self.operator = _ensure_user(
			f"nxr-fund-selector-operator-{marker}@example.test",
			"NEXORA Finance Operator",
		)
		self.manager = _ensure_user(
			f"nxr-fund-selector-manager-{marker}@example.test",
			"NEXORA Finance Manager",
		)

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _project(self, name: str) -> str:
		return str(
			frappe.get_doc(
				{
					"doctype": "Project",
					"project_name": name,
					"status": "Open",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def _source(self, project: str, amount: int, source_name: str) -> str:
		frappe.set_user(self.operator)
		return str(
			create_fund_source(
				{
					"idempotency_key": _key("fund-selector-source"),
					"source_name": source_name,
					"channel": "Cash",
					"project": project,
					"source_date": frappe.utils.today(),
					"currency": "HNL",
					"original_amount": amount,
					"exchange_rate": 1,
					"origin_or_sender": "Prueba selector de fondos",
					"custodian": self.operator,
				}
			)["fund_source"]
		)

	def test_selector_returns_only_eligible_sources_for_selected_project(self) -> None:
		active = self._source(self.project, 100_000, "Fondo disponible")
		cancelled = self._source(self.project, 80_000, "Fondo anulado")
		other = self._source(self.other_project, 50_000, "Fondo de otro proyecto")

		frappe.set_user(self.manager)
		cancel_fund_source(
			cancelled,
			"Ingreso duplicado anulado para probar el selector",
			_key("fund-selector-cancel"),
		)

		frappe.set_user(self.operator)
		rows = list_source_balances(self.project)
		by_source = {row["source"]: row for row in rows}

		self.assertIn(active, by_source)
		self.assertNotIn(cancelled, by_source)
		self.assertNotIn(other, by_source)
		self.assertEqual("100000.00", by_source[active]["balance_hnl"])
		self.assertEqual("0.00", by_source[active]["reserved_hnl"])
		self.assertEqual("100000.00", by_source[active]["available_hnl"])

	def test_selector_empty_state_and_permission_denial(self) -> None:
		frappe.set_user(self.operator)
		self.assertEqual([], list_source_balances(self.empty_project))

		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			list_source_balances(self.project)


if __name__ == "__main__":
	import unittest

	unittest.main()
