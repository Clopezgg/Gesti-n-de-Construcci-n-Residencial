from __future__ import annotations

import json
import pathlib

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestGoodsReceiptContract:
	def test_receipt_state_machine_is_defined(self) -> None:
		from nexora.purchases.receipt_core import GOODS_RECEIPT_TRANSITIONS

		assert "Draft" in GOODS_RECEIPT_TRANSITIONS
		assert "Completed" in GOODS_RECEIPT_TRANSITIONS
		assert "Cancelled" in GOODS_RECEIPT_TRANSITIONS

	def test_receipt_doctype_is_defined(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_goods_receipt/nxr_goods_receipt.json"
		assert path.is_file()
		payload = json.loads(path.read_text(encoding="utf-8"))
		assert payload["doctype"] == "DocType"
		assert payload["name"] == "NXR Goods Receipt"
		assert payload["module"] == "NEXORA"

	def test_receipt_line_doctype_is_defined(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_goods_receipt_line/nxr_goods_receipt_line.json"
		assert path.is_file()
		payload = json.loads(path.read_text(encoding="utf-8"))
		assert payload["name"] == "NXR Goods Receipt Line"
		assert payload["istable"] == 1

	def test_receipt_controller_enforces_boundary(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_goods_receipt/nxr_goods_receipt.py"
		code = path.read_text(encoding="utf-8")
		assert "require_service_write" in code
		assert "on_trash" in code

	def test_receipt_service_exposes_lifecycle(self) -> None:
		from nexora.purchases.receipt_service import (
			create_receipt,
			get_receipt,
			list_receipts,
			transition_receipt,
		)

		assert callable(create_receipt)
		assert callable(transition_receipt)
		assert callable(get_receipt)
		assert callable(list_receipts)

	def test_receipt_line_tracks_ordered_and_received(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_goods_receipt_line/nxr_goods_receipt_line.json"
		payload = json.loads(path.read_text(encoding="utf-8"))
		field_names = {f["fieldname"] for f in payload["fields"]}
		assert "ordered_quantity" in field_names
		assert "previously_received" in field_names
		assert "quantity" in field_names
		assert "rejected_quantity" in field_names
		assert "accepted_quantity" in field_names
