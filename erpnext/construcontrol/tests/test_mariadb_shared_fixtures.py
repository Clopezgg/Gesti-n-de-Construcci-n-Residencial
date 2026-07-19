from __future__ import annotations

from frappe.tests.utils import FrappeTestCase

from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

# The two inherited Pick List packed-item tests use RJ Warehouse but do not
# declare it as their own fixture. Running this module before the sharded suite
# makes that shared dependency explicit and independent from test ordering.
test_dependencies = ["Warehouse"]


class TestMariaDBSharedFixtures(FrappeTestCase):
	def test_prepare_pick_list_warehouse(self) -> None:
		warehouse = create_warehouse("RJ Warehouse")
		self.assertEqual(warehouse, "RJ Warehouse - _TC")
