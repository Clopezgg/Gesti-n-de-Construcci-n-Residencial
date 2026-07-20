from __future__ import annotations

from frappe.tests.utils import FrappeTestCase

from erpnext.construcontrol.tests.runtime_smoke import run as run_construcontrol_runtime_smoke
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

# The two inherited Pick List packed-item tests use RJ Warehouse but do not
# declare it as their own fixture. Running this module before the sharded suite
# makes that shared dependency explicit and independent from test ordering.
test_dependencies = ["Warehouse"]


class TestMariaDBSharedFixtures(FrappeTestCase):
	def test_prepare_pick_list_warehouse(self) -> None:
		warehouse = create_warehouse("RJ Warehouse")
		self.assertEqual(warehouse, "RJ Warehouse - _TC")

	def test_construcontrol_finance_permissions_and_runtime_contract(self) -> None:
		result = run_construcontrol_runtime_smoke()
		self.assertTrue(result["ok"])
		self.assertEqual(result["funding_net_hnl"], 1000.0)
		self.assertEqual(result["expense_total_hnl"], 250.0)
		self.assertEqual(result["available_hnl"], 750.0)
		self.assertEqual(result["payable_status"], "paid")
		self.assertGreaterEqual(result["permission_denials"], 2)
