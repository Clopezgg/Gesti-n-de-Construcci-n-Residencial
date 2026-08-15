from __future__ import annotations

import inspect
import json
import pathlib

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent
REPO_ROOT = APP_ROOT.parents[2]


class TestFinalCorrectionsContract:
	def test_release_gates_and_current_state_exist(self) -> None:
		docs = REPO_ROOT / "docs/nexora"
		assert (docs / "RELEASE_GATES.md").is_file()
		assert (docs / "CURRENT_STATE.md").is_file()

	def test_canonical_command_and_evidence_flows_are_not_duplicated(self) -> None:
		hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
		assert "nexora_shell.js" in hooks
		assert "nexora_command_bar.js" not in hooks
		assert "nexora_mobile_evidence.js" not in hooks
		assert not (APP_ROOT / "public/js/nexora_command_bar.js").exists()
		assert not (APP_ROOT / "public/js/nexora_mobile_evidence.js").exists()

	def test_goods_receipt_requires_warehouse(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_goods_receipt/nxr_goods_receipt.json"
		payload = json.loads(path.read_text(encoding="utf-8"))
		field = next(f for f in payload["fields"] if f["fieldname"] == "warehouse")
		assert field["options"] == "NXR Warehouse"
		assert field["reqd"] == 1
		service = inspect.getsource(__import__("nexora.purchases.receipt_service", fromlist=["create_receipt"]).create_receipt)
		assert '_ensure_link("NXR Warehouse", data.get("warehouse")' in service

	def test_goods_receipt_reversal_is_outbound(self) -> None:
		from nexora.inventory.core import OUTGOING_STOCK_TRANSACTION_TYPES
		from nexora.purchases import inventory_bridge

		assert "Receipt Reversal" in OUTGOING_STOCK_TRANSACTION_TYPES
		assert 'source_type = "Receipt Reversal"' in inspect.getsource(inventory_bridge.sync_goods_receipt_inventory)

	def test_quantity_precision_is_preserved_in_purchase_and_receipt_validation(self) -> None:
		from nexora.purchases import order_core, receipt_core

		assert "from nexora.inventory.core import quantity" in inspect.getsource(order_core)
		assert "from nexora.inventory.core import quantity" in inspect.getsource(receipt_core)
		assert "line_quantity = quantity" in inspect.getsource(receipt_core.validate_receipt_lines)

	def test_purchase_payment_requires_idempotency(self) -> None:
		from nexora.purchases import financial_bridge

		code = inspect.getsource(financial_bridge.pay_purchase_order)
		assert 'key = str(data.get("idempotency_key") or "").strip()' in code
		assert "execute_commitment" in code
