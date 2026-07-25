from __future__ import annotations

from decimal import Decimal
from unittest import TestCase

from nexora.purchases.order_core import (
	PurchaseValidationError,
	assert_order_transition,
	money,
	order_line_amounts,
	tolerance_range,
)


class TestPurchaseOrderCore(TestCase):
	def test_draft_can_be_confirmed(self) -> None:
		try:
			assert_order_transition("Draft", "Confirmed")
		except PurchaseValidationError:
			self.fail("Draft -> Confirmed debería ser válido")

	def test_draft_can_be_cancelled(self) -> None:
		try:
			assert_order_transition("Draft", "Cancelled")
		except PurchaseValidationError:
			self.fail("Draft -> Cancelled debería ser válido")

	def test_confirmed_can_be_approved(self) -> None:
		try:
			assert_order_transition("Confirmed", "Approved")
		except PurchaseValidationError:
			self.fail("Confirmed -> Approved debería ser válido")

	def test_approved_can_be_sent(self) -> None:
		try:
			assert_order_transition("Approved", "Sent")
		except PurchaseValidationError:
			self.fail("Approved -> Sent debería ser válido")

	def test_sent_can_be_completed(self) -> None:
		try:
			assert_order_transition("Sent", "Completed")
		except PurchaseValidationError:
			self.fail("Sent -> Completed debería ser válido")

	def test_completed_is_terminal(self) -> None:
		with self.assertRaises(PurchaseValidationError):
			assert_order_transition("Completed", "Draft")
		with self.assertRaises(PurchaseValidationError):
			assert_order_transition("Completed", "Cancelled")

	def test_cancelled_is_terminal(self) -> None:
		with self.assertRaises(PurchaseValidationError):
			assert_order_transition("Cancelled", "Draft")

	def test_direct_approval_is_rejected(self) -> None:
		with self.assertRaises(PurchaseValidationError):
			assert_order_transition("Draft", "Approved")

	def test_line_amounts_are_exact(self) -> None:
		lines = [
			{"quantity": "10", "unit_rate": "100.50", "charge_amount": "0", "tax_rate": "15"},
		]
		result = order_line_amounts(lines)
		self.assertEqual(1, len(result))
		self.assertEqual(money("1005.00"), result[0].amount)
		self.assertEqual(money("150.75"), result[0].tax_amount)
		self.assertEqual(money("0"), result[0].discount_amount)
		self.assertEqual(money("1155.75"), result[0].net_amount)

	def test_line_amounts_with_discount(self) -> None:
		lines = [
			{"quantity": "5", "unit_rate": "200", "charge_amount": "0", "discount_rate": "10"},
		]
		result = order_line_amounts(lines)
		self.assertEqual(money("1000.00"), result[0].amount)
		self.assertEqual(money("100.00"), result[0].discount_amount)
		self.assertEqual(money("900.00"), result[0].net_amount)

	def test_line_amounts_with_charge(self) -> None:
		lines = [
			{"quantity": "1", "unit_rate": "1000", "charge_amount": "50", "tax_rate": "0"},
		]
		result = order_line_amounts(lines)
		self.assertEqual(money("1050.00"), result[0].net_amount)

	def test_negative_quantity_is_rejected(self) -> None:
		with self.assertRaises(PurchaseValidationError):
			order_line_amounts([{"quantity": "-5", "unit_rate": "100"}])

	def test_negative_unit_rate_is_rejected(self) -> None:
		with self.assertRaises(PurchaseValidationError):
			order_line_amounts([{"quantity": "5", "unit_rate": "-10"}])

	def test_negative_net_amount_is_rejected(self) -> None:
		with self.assertRaises(PurchaseValidationError):
			order_line_amounts(
				[{"quantity": "1", "unit_rate": "100", "charge_amount": "0", "discount_rate": "200"}]
			)

	def test_empty_lines_are_rejected(self) -> None:
		with self.assertRaises(PurchaseValidationError):
			order_line_amounts([])

	def test_tolerance_default_range(self) -> None:
		min_q, max_q = tolerance_range(money("100"))
		self.assertEqual(money("90"), min_q)
		self.assertEqual(money("110"), max_q)

	def test_tolerance_custom_range(self) -> None:
		min_q, max_q = tolerance_range(money("100"), Decimal(5))
		self.assertEqual(money("95"), min_q)
		self.assertEqual(money("105"), max_q)
