from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.dashboard.executive import get_executive_snapshot
from nexora.financial.sources import cancel_fund_source, create_fund_source


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
	return email


class TestDashboardNetIncomeMariaDB(FrappeTestCase):
	def setUp(self) -> None:
		super().setUp()
		frappe.set_user("Administrator")
		marker = uuid.uuid4().hex[:10]
		self.project = self._project(f"_Test NEXORA Net Income {marker}")
		self.other_project = self._project(f"_Test NEXORA Net Income Other {marker}")
		self.operator = _ensure_user(
			f"nxr-net-income-operator-{marker}@example.test",
			"NEXORA Finance Operator",
		)
		self.manager = _ensure_user(
			f"nxr-net-income-manager-{marker}@example.test",
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

	def _source(self, project: str, amount: int) -> str:
		frappe.set_user(self.operator)
		return str(
			create_fund_source(
				{
					"idempotency_key": _key("net-income-source"),
					"source_name": f"Fuente neta {uuid.uuid4().hex[:8]}",
					"channel": "Transfer",
					"project": project,
					"source_date": frappe.utils.today(),
					"currency": "HNL",
					"original_amount": amount,
					"exchange_rate": 1,
					"origin_or_sender": "Prueba de ingreso neto",
					"custodian": self.operator,
					"institution": "Banco de prueba",
					"account_reference": "Cuenta de prueba 0001",
					"external_reference": _key("net-income-transfer"),
				}
			)["fund_source"]
		)

	def _cancel(self, source: str) -> None:
		frappe.set_user(self.manager)
		cancel_fund_source(
			source,
			"Ingreso duplicado anulado para validar el total neto",
			_key("net-income-cancel"),
		)

	def test_dashboard_reports_active_income_after_cancellation(self) -> None:
		self._source(self.project, 100_000)
		cancelled = self._source(self.project, 80_000)
		self._cancel(cancelled)

		frappe.set_user(self.manager)
		snapshot = get_executive_snapshot(
			{
				"project": self.project,
				"from_date": frappe.utils.today(),
				"to_date": frappe.utils.today(),
			}
		)

		self.assertEqual(180_000, snapshot["executive"]["gross_received_hnl"])
		self.assertEqual(80_000, snapshot["executive"]["reversed_inflow_hnl"])
		self.assertEqual(100_000, snapshot["executive"]["net_received_hnl"])
		self.assertEqual(100_000, snapshot["executive"]["received_hnl"])
		self.assertEqual(100_000, snapshot["finance"]["inflows_hnl"])
		self.assertEqual(
			[{"label": "Transfer", "amount_hnl": 100_000.0}],
			snapshot["analytics"]["income_by_channel"],
		)
		self.assertEqual(80_000, snapshot["analytics"]["source_totals"]["reversed_hnl"])

	def test_cancellation_from_another_project_is_not_subtracted(self) -> None:
		self._source(self.project, 100_000)
		other_cancelled = self._source(self.other_project, 50_000)
		self._cancel(other_cancelled)

		frappe.set_user(self.manager)
		snapshot = get_executive_snapshot(
			{
				"project": self.project,
				"from_date": frappe.utils.today(),
				"to_date": frappe.utils.today(),
			}
		)

		self.assertEqual(100_000, snapshot["executive"]["gross_received_hnl"])
		self.assertEqual(0, snapshot["executive"]["reversed_inflow_hnl"])
		self.assertEqual(100_000, snapshot["executive"]["net_received_hnl"])


if __name__ == "__main__":
	import unittest

	unittest.main()
