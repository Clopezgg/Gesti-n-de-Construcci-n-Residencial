from __future__ import annotations

import ast
import json
import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


def _action_roles() -> dict[str, str]:
	module = ast.parse((APP_ROOT / "permissions.py").read_text(encoding="utf-8"))
	for node in module.body:
		if isinstance(node, ast.Assign):
			for target in node.targets:
				if isinstance(target, ast.Name) and target.id == "ACTION_ROLES":
					return {
						key.value: value.id
						for key, value in zip(node.value.keys, node.value.values, strict=True)
						if isinstance(key, ast.Constant) and isinstance(value, ast.Name)
					}
	raise AssertionError("ACTION_ROLES no encontrado")


class TestInventoryContract(unittest.TestCase):
	def test_inventory_module_exists(self) -> None:
		init = APP_ROOT / "inventory/__init__.py"
		self.assertTrue(init.is_file())

	def test_inventory_core_exists(self) -> None:
		core = APP_ROOT / "inventory/core.py"
		self.assertTrue(core.is_file())

	def test_inventory_service_exists(self) -> None:
		service = APP_ROOT / "inventory/service.py"
		self.assertTrue(service.is_file())

	def test_warehouse_doctype_is_defined(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_warehouse/nxr_warehouse.json"
		self.assertTrue(path.is_file())
		payload = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual("NXR Warehouse", payload["name"])

	def test_warehouse_controller_enforces_boundary(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_warehouse/nxr_warehouse.py"
		code = path.read_text(encoding="utf-8")
		self.assertIn("require_service_write", code)
		self.assertIn("on_trash", code)

	def test_stock_transaction_doctype_is_defined(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_stock_transaction/nxr_stock_transaction.json"
		self.assertTrue(path.is_file())
		payload = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual("NXR Stock Transaction", payload["name"])

	def test_stock_transaction_controller_enforces_boundary(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_stock_transaction/nxr_stock_transaction.py"
		code = path.read_text(encoding="utf-8")
		self.assertIn("require_service_write", code)
		self.assertIn("on_trash", code)

	def test_stock_transaction_line_is_table(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_stock_transaction_line/nxr_stock_transaction_line.json"
		self.assertTrue(path.is_file())
		payload = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual("NXR Stock Transaction Line", payload["name"])
		self.assertEqual(1, payload["istable"])

	def test_stock_transaction_line_has_tracking_fields(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_stock_transaction_line/nxr_stock_transaction_line.json"
		payload = json.loads(path.read_text(encoding="utf-8"))
		field_names = {f["fieldname"] for f in payload["fields"]}
		for field in (
			"item",
			"warehouse",
			"quantity",
			"unit_rate",
			"amount",
			"batch_no",
			"reference_doctype",
			"reference_name",
		):
			self.assertIn(field, field_names)

	def test_outgoing_movements_are_checked_against_a_negative_balance_before_completing(self) -> None:
		service = (APP_ROOT / "inventory/service.py").read_text(encoding="utf-8")
		self.assertIn("_assert_no_negative_balance(doc)", service)
		self.assertIn("validate_item_balance(", service)
		transition_at = service.index("def transition_stock_transaction(")
		guard_call_at = service.index("_assert_no_negative_balance(doc)")
		save_at = service.index("doc.status = target")
		self.assertLess(transition_at, guard_call_at)
		self.assertLess(guard_call_at, save_at)

	def test_negative_balance_guard_only_applies_to_outgoing_transaction_types(self) -> None:
		from nexora.inventory.core import INCOMING_STOCK_TRANSACTION_TYPES, OUTGOING_STOCK_TRANSACTION_TYPES

		self.assertEqual(
			INCOMING_STOCK_TRANSACTION_TYPES,
			{"Receipt", "Transfer In", "Return"},
		)
		self.assertEqual(
			OUTGOING_STOCK_TRANSACTION_TYPES,
			{"Receipt Reversal", "Transfer Out", "Issue to Contractor", "Consumption", "Damage", "Loss"},
		)

	def test_inventory_service_uses_specific_server_side_actions(self) -> None:
		permissions = (APP_ROOT / "permissions.py").read_text(encoding="utf-8")
		service = (APP_ROOT / "inventory/service.py").read_text(encoding="utf-8")
		for action in (
			"manage_warehouse",
			"create_stock_transaction",
			"submit_stock_transaction",
		):
			self.assertIn(f'"{action}"', permissions)
			self.assertIn(f'require_action("{action}")', service)
		self.assertNotIn('require_action("create_purchase_request")', service)
		self.assertNotIn('require_action("submit_purchase_request")', service)

	def test_purchase_request_operator_cannot_manage_warehouses_or_complete_stock(self) -> None:
		actions = _action_roles()
		self.assertEqual("OPERATOR_ROLES", actions["create_purchase_request"])
		self.assertEqual("OPERATOR_ROLES", actions["submit_purchase_request"])
		self.assertEqual("MANAGER_ROLES", actions["manage_warehouse"])
		self.assertEqual("OPERATOR_ROLES", actions["create_stock_transaction"])
		self.assertEqual("MANAGER_ROLES", actions["submit_stock_transaction"])
