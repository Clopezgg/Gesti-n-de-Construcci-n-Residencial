from __future__ import annotations

from unittest import TestCase

from nexora.purchases.receipt_core import (
	GOODS_RECEIPT_TRANSITIONS,
	PurchaseValidationError,
	assert_receipt_transition,
	validate_receipt_lines,
)


class TestGoodsReceiptCore(TestCase):
	def test_draft_can_be_completed(self) -> None:
		try:
			assert_receipt_transition("Draft", "Completed")
		except PurchaseValidationError:
			self.fail("Draft -> Completed debería ser válido")

	def test_draft_can_be_cancelled(self) -> None:
		try:
			assert_receipt_transition("Draft", "Cancelled")
		except PurchaseValidationError:
			self.fail("Draft -> Cancelled debería ser válido")

	def test_completed_is_terminal(self) -> None:
		with self.assertRaises(PurchaseValidationError):
			assert_receipt_transition("Completed", "Draft")

	def test_cancelled_is_terminal(self) -> None:
		with self.assertRaises(PurchaseValidationError):
			assert_receipt_transition("Cancelled", "Draft")

	def test_all_transitions_are_defined(self) -> None:
		for state, targets in GOODS_RECEIPT_TRANSITIONS.items():
			for target in targets:
				try:
					assert_receipt_transition(state, target)
				except PurchaseValidationError:
					self.fail(f"{state} -> {target} debería ser válido")

	def test_unknown_source_is_rejected(self) -> None:
		with self.assertRaises(PurchaseValidationError):
			assert_receipt_transition("Unknown", "Draft")

	def test_validate_receipt_lines_within_tolerance(self) -> None:
		order_lines = [{"name": "L001", "quantity": "100", "line_code": "001"}]
		lines = [{"purchase_order_line": "L001", "quantity": "105", "rejected_quantity": "0"}]
		result = validate_receipt_lines(lines, order_lines)
		self.assertIn("L001", result)
		self.assertEqual("105.00", str(result["L001"]))

	def test_validate_receipt_lines_exceeds_tolerance(self) -> None:
		order_lines = [{"name": "L001", "quantity": "100", "line_code": "001"}]
		lines = [{"purchase_order_line": "L001", "quantity": "120", "rejected_quantity": "0"}]
		with self.assertRaises(PurchaseValidationError):
			validate_receipt_lines(lines, order_lines)

	def test_negative_quantity_rejected(self) -> None:
		order_lines = [{"name": "L001", "quantity": "100", "line_code": "001"}]
		with self.assertRaises(PurchaseValidationError):
			validate_receipt_lines(
				[{"purchase_order_line": "L001", "quantity": "-5", "rejected_quantity": "0"}], order_lines
			)

	def test_negative_rejected_rejected(self) -> None:
		order_lines = [{"name": "L001", "quantity": "100", "line_code": "001"}]
		with self.assertRaises(PurchaseValidationError):
			validate_receipt_lines(
				[{"purchase_order_line": "L001", "quantity": "10", "rejected_quantity": "-1"}], order_lines
			)

	def test_no_purchase_order_line_ref_rejected(self) -> None:
		with self.assertRaises(PurchaseValidationError):
			validate_receipt_lines(
				[{"purchase_order_line": "", "quantity": "10", "rejected_quantity": "0"}], []
			)
