from __future__ import annotations

import inspect
import json
import pathlib

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestPurchaseFinancialBridgeContract:
	def test_purchase_order_exposes_commitment_fields(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_purchase_order/nxr_purchase_order.json"
		payload = json.loads(path.read_text(encoding="utf-8"))
		fields = {field["fieldname"] for field in payload["fields"]}
		assert {
			"fund_source",
			"financial_commitment",
			"commitment_reserved_hnl",
			"commitment_executed_hnl",
		} <= fields

	def test_commitment_exposes_origin_reference(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_commitment/nxr_commitment.json"
		payload = json.loads(path.read_text(encoding="utf-8"))
		fields = {field["fieldname"] for field in payload["fields"]}
		assert {"reference_doctype", "reference_name"} <= fields

	def test_purchase_financial_bridge_is_registered(self) -> None:
		hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
		assert "doc_events" in hooks
		assert "NXR Purchase Order" in hooks
		assert "nexora.purchases.financial_bridge.sync_purchase_order_financials" in hooks

	def test_purchase_payment_endpoint_exists_and_is_server_side(self) -> None:
		from nexora.purchases import financial_bridge

		assert callable(financial_bridge.pay_purchase_order)
		assert "frappe.whitelist" in inspect.getsource(financial_bridge.pay_purchase_order)
		code = inspect.getsource(financial_bridge.pay_purchase_order)
		assert "require_project_access" in code
		assert 'require_action("execute")' in code
		assert "execute_commitment" in code
		assert "commitment_outstanding" in code
		assert "_received_amount" in code

	def test_purchase_bridge_never_uses_a_second_ledger(self) -> None:
		code = (APP_ROOT / "nexora/purchases/financial_bridge.py").read_text(encoding="utf-8")
		assert "NXR Operation" in code
		assert "execute_commitment" in code
		assert "Stock Ledger" not in code
