from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.dashboard.snapshot_query import get_executive_snapshot
from nexora.financial.operations import execute_financial_operation
from nexora.financial.sources import create_fund_source
from nexora.reports.canonical_views import get_cost_report, reconcile_totals
from nexora.reports.safe_export import export_report


def _key(prefix: str) -> str:
	return f"{prefix}-{uuid.uuid4().hex}"


def _user(email: str, role: str) -> str:
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


class TestFilteredExecutiveSnapshotMariaDB(FrappeTestCase):
	def setUp(self) -> None:
		super().setUp()
		frappe.set_user("Administrator")
		marker = uuid.uuid4().hex[:10]
		self.project = str(
			frappe.get_doc(
				{
					"doctype": "Project",
					"project_name": f"_Test NEXORA Filters {marker}",
					"status": "Open",
				}
			).insert(ignore_permissions=True).name
		)
		self.operator = _user(
			f"nxr-filter-operator-{marker}@example.test",
			"NEXORA Finance Operator",
		)
		self.manager = _user(
			f"nxr-filter-manager-{marker}@example.test",
			"NEXORA Finance Manager",
		)
		self.viewer = _user(
			f"nxr-filter-viewer-{marker}@example.test",
			"NEXORA Project Viewer",
		)

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _source(self, amount: int) -> str:
		frappe.set_user(self.operator)
		return str(
			create_fund_source(
				{
					"idempotency_key": _key("filter-source"),
					"source_name": f"Fuente filtro {uuid.uuid4().hex[:8]}",
					"channel": "Remittance",
					"project": self.project,
					"source_date": frappe.utils.today(),
					"currency": "HNL",
					"original_amount": amount,
					"exchange_rate": 1,
					"origin_or_sender": "Prueba de filtros",
					"custodian": self.operator,
				}
			)["fund_source"]
		)

	def test_source_filter_aligns_kpis_charts_details_exports_and_reconciliation(self) -> None:
		first = self._source(600)
		second = self._source(400)
		frappe.set_user(self.operator)
		execute_financial_operation(
			{
				"idempotency_key": _key("filter-outflow"),
				"operation_type": "Outflow",
				"operation_date": frappe.utils.today(),
				"project": self.project,
				"amount_hnl": 100,
				"allocations": [
					{"source": first, "amount_hnl": 60},
					{"source": second, "amount_hnl": 40},
				],
				"requester": self.operator,
				"approved_by": self.manager,
			}
		)
		filters = {
			"project": self.project,
			"source": first,
			"from_date": frappe.utils.today(),
			"to_date": frappe.utils.today(),
		}
		result = get_executive_snapshot(filters)
		self.assertEqual(600, result["executive"]["received_hnl"])
		self.assertEqual(60, result["executive"]["spent_hnl"])
		self.assertEqual(540, result["executive"]["cash_available_hnl"])
		self.assertEqual(540, result["executive"]["projected_available_hnl"])
		self.assertEqual(60, result["analytics"]["expense_rows"][0]["amount_hnl"])
		self.assertEqual(first, result["analytics"]["expense_rows"][0]["sources"])
		self.assertEqual(0, result["pending_accounts"]["total_hnl"])
		self.assertTrue(result["filter_context"]["source_kpis_filtered"])

		cost_report = get_cost_report(filters)
		self.assertEqual(60, cost_report["total"])
		self.assertEqual(first, cost_report["filter_context"]["active"]["source"])
		reconciliation = reconcile_totals(filters)
		self.assertEqual(600, reconciliation["inflows"])
		self.assertEqual(60, reconciliation["outflows"])
		self.assertEqual(540, reconciliation["net"])

		frappe.set_user(self.manager)
		export_report({**filters, "report_code": "FI02", "format": "xlsx"})
		self.assertTrue(frappe.local.response.filename.startswith("NEXORA-FI02-"))
		self.assertTrue(frappe.local.response.filecontent)
		self.assertEqual("download", frappe.local.response.type)

	def test_unscoped_project_viewer_is_rejected(self) -> None:
		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			get_executive_snapshot(
				{
					"project": self.project,
					"from_date": frappe.utils.today(),
					"to_date": frappe.utils.today(),
				}
			)
