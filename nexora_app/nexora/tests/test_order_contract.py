from __future__ import annotations

import json
import ast
import pathlib

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


class TestPurchaseOrderContract:
	def test_order_state_machine_is_defined(self) -> None:
		from nexora.purchases.order_core import PURCHASE_ORDER_TRANSITIONS

		assert "Draft" in PURCHASE_ORDER_TRANSITIONS
		assert "Confirmed" in PURCHASE_ORDER_TRANSITIONS
		assert "Approved" in PURCHASE_ORDER_TRANSITIONS
		assert "Sent" in PURCHASE_ORDER_TRANSITIONS
		assert "Completed" in PURCHASE_ORDER_TRANSITIONS
		assert "Cancelled" in PURCHASE_ORDER_TRANSITIONS

	def test_order_doctype_is_defined(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_purchase_order/nxr_purchase_order.json"
		assert path.is_file()
		payload = json.loads(path.read_text(encoding="utf-8"))
		assert payload["doctype"] == "DocType"
		assert payload["name"] == "NXR Purchase Order"
		assert payload["module"] == "NEXORA"

	def test_order_line_doctype_is_defined(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_purchase_order_line/nxr_purchase_order_line.json"
		assert path.is_file()
		payload = json.loads(path.read_text(encoding="utf-8"))
		assert payload["name"] == "NXR Purchase Order Line"
		assert payload["istable"] == 1

	def test_order_controller_enforces_boundary(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_purchase_order/nxr_purchase_order.py"
		code = path.read_text(encoding="utf-8")
		assert "require_service_write" in code
		assert "on_trash" in code

	def test_order_service_exposes_lifecycle(self) -> None:
		from nexora.purchases.order_service import create_order, get_order, list_orders, transition_order

		assert callable(create_order)
		assert callable(transition_order)
		assert callable(get_order)
		assert callable(list_orders)

	def test_order_service_has_whitelist_decorators(self) -> None:
		import inspect

		from nexora.purchases import order_service

		source = inspect.getsource(order_service.create_order)
		assert "frappe.whitelist" in source

	def test_order_doctype_has_tax_and_discount_fields(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_purchase_order_line/nxr_purchase_order_line.json"
		payload = json.loads(path.read_text(encoding="utf-8"))
		field_names = {f["fieldname"] for f in payload["fields"]}
		assert "tax_rate" in field_names
		assert "tax_amount" in field_names
		assert "discount_rate" in field_names
		assert "discount_amount" in field_names
		assert "charge_amount" in field_names
		assert "net_amount" in field_names
		assert "tolerance_percentage" in field_names

	def test_order_service_uses_specific_server_side_actions(self) -> None:
		permissions = (APP_ROOT / "permissions.py").read_text(encoding="utf-8")
		service = (APP_ROOT / "purchases/order_service.py").read_text(encoding="utf-8")
		for action in (
			"create_purchase_order",
			"submit_purchase_order",
			"approve_purchase_order",
		):
			assert f'"{action}"' in permissions
			assert f'require_action("{action}")' in service
		assert 'require_action("create_purchase_request")' not in service
		assert 'require_action("submit_purchase_request")' not in service
		assert 'require_action("approve_purchase_request")' not in service

	def test_purchase_request_operator_cannot_create_or_approve_orders(self) -> None:
		actions = _action_roles()
		assert actions["create_purchase_request"] == "OPERATOR_ROLES"
		assert actions["submit_purchase_request"] == "OPERATOR_ROLES"
		assert actions["create_purchase_order"] == "MANAGER_ROLES"
		assert actions["submit_purchase_order"] == "MANAGER_ROLES"
		assert actions["approve_purchase_order"] == "MANAGER_ROLES"
