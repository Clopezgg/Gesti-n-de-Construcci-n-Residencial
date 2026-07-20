from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "inventory.py"
SPEC = importlib.util.spec_from_file_location("cc_inventory", MODULE)
INVENTORY = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(INVENTORY)


class InventoryContractTest(unittest.TestCase):
	def test_receipt_consumption_return_and_adjustment_reconcile_quantity_and_value(self):
		snapshot = INVENTORY.inventory_snapshot(
			10,
			20,
			[
				{"movement_type": "receipt", "quantity": 10, "unit_cost_hnl": 30},
				{"movement_type": "consumption", "quantity": 5},
				{"movement_type": "return_in", "quantity": 2, "unit_cost_hnl": 25},
				{"movement_type": "adjustment_out", "quantity": 1},
			],
			low_stock_threshold=4,
		)
		self.assertEqual(snapshot["current_qty"], 16)
		self.assertAlmostEqual(snapshot["current_value_hnl"], 400, places=2)
		self.assertAlmostEqual(snapshot["unit_cost_hnl"], 25, places=6)
		self.assertEqual(snapshot["stock_status"], "available")

	def test_transfer_is_neutral_globally_and_moves_stock_between_warehouses(self):
		rows = [
			{
				"movement_type": "transfer",
				"quantity": 4,
				"warehouse": "Principal",
				"target_warehouse": "Obra",
			}
		]
		self.assertEqual(INVENTORY.inventory_snapshot(10, 15, rows)["current_qty"], 10)
		self.assertEqual(INVENTORY.warehouse_balance("Principal", 10, rows, "Principal"), 6)
		self.assertEqual(INVENTORY.warehouse_balance("Principal", 10, rows, "Obra"), 4)

	def test_negative_stock_is_rejected_globally_and_by_warehouse(self):
		with self.assertRaisesRegex(ValueError, "inventario negativo"):
			INVENTORY.inventory_snapshot(
				2,
				10,
				[{"movement_type": "consumption", "quantity": 3}],
			)
		with self.assertRaisesRegex(ValueError, "supera la existencia"):
			INVENTORY.validate_movement_contract(
				{
					"project": "P1",
					"material": "M1",
					"movement_type": "consumption",
					"quantity": 3,
					"warehouse": "B1",
					"movement_reference": "OUT-1",
				},
				available_quantity=2,
			)

	def test_adjustment_requires_manager_reason_contract_and_transfer_requires_distinct_target(self):
		with self.assertRaisesRegex(ValueError, "justificación"):
			INVENTORY.validate_movement_contract(
				{
					"project": "P1",
					"material": "M1",
					"movement_type": "adjustment_in",
					"quantity": 1,
					"warehouse": "B1",
					"movement_reference": "ADJ-1",
				},
				available_quantity=0,
			)
		with self.assertRaisesRegex(ValueError, "deben ser diferentes"):
			INVENTORY.validate_movement_contract(
				{
					"project": "P1",
					"material": "M1",
					"movement_type": "transfer",
					"quantity": 1,
					"warehouse": "B1",
					"target_warehouse": "B1",
					"movement_reference": "TR-1",
				},
				available_quantity=1,
			)

	def test_duplicate_fingerprint_is_stable_and_sensitive_to_warehouse(self):
		base = {
			"project": "P1",
			"material": "M1",
			"movement_type": "Recepción",
			"quantity": 2,
			"warehouse": "B1",
			"movement_reference": " OC-100 ",
		}
		first = INVENTORY.movement_fingerprint(base)
		second = INVENTORY.movement_fingerprint({**base, "movement_type": "receipt"})
		other = INVENTORY.movement_fingerprint({**base, "warehouse": "B2"})
		self.assertEqual(first, second)
		self.assertNotEqual(first, other)

	def test_logically_deleted_movements_do_not_change_stock(self):
		snapshot = INVENTORY.inventory_snapshot(
			5,
			10,
			[
				{
					"movement_type": "consumption",
					"quantity": 5,
					"is_logically_deleted": 1,
				}
			],
		)
		self.assertEqual(snapshot["current_qty"], 5)
		self.assertEqual(snapshot["current_value_hnl"], 50)


if __name__ == "__main__":
	unittest.main()
