from __future__ import annotations

from unittest import TestCase

from nexora.inventory.core import (
	STOCK_TRANSACTION_TRANSITIONS,
	PurchaseValidationError,
	StockBalance,
	assert_stock_transition,
	money,
	quantity,
	validate_item_balance,
)


class TestInventoryCore(TestCase):
	def test_draft_can_be_completed(self) -> None:
		try:
			assert_stock_transition("Draft", "Completed")
		except PurchaseValidationError:
			self.fail("Draft -> Completed debería ser válido")

	def test_draft_can_be_cancelled(self) -> None:
		try:
			assert_stock_transition("Draft", "Cancelled")
		except PurchaseValidationError:
			self.fail("Draft -> Cancelled debería ser válido")

	def test_completed_is_terminal(self) -> None:
		with self.assertRaises(PurchaseValidationError):
			assert_stock_transition("Completed", "Draft")

	def test_cancelled_is_terminal(self) -> None:
		with self.assertRaises(PurchaseValidationError):
			assert_stock_transition("Cancelled", "Draft")

	def test_all_states_have_transitions(self) -> None:
		for state, targets in STOCK_TRANSACTION_TRANSITIONS.items():
			for target in targets:
				try:
					assert_stock_transition(state, target)
				except PurchaseValidationError:
					self.fail(f"{state} -> {target} debería ser válido")

	def test_unknown_state_is_rejected(self) -> None:
		with self.assertRaises(PurchaseValidationError):
			assert_stock_transition("Unknown", "Draft")

	def test_money_rounds_to_two_decimals(self) -> None:
		self.assertEqual("150.00", str(money("150")))
		self.assertEqual("150.25", str(money("150.25")))
		self.assertEqual("150.26", str(money("150.256")))

	def test_quantity_rounds_to_six_decimals(self) -> None:
		self.assertEqual("1.000000", str(quantity("1")))
		self.assertEqual("0.000001", str(quantity("0.000001")))

	def test_invalid_money_is_rejected(self) -> None:
		with self.assertRaises(PurchaseValidationError):
			money("not-a-number")

	def test_validate_item_balance_allows_sufficient(self) -> None:
		try:
			validate_item_balance("ITEM-001", "WH-001", money("100"), money("50"))
		except PurchaseValidationError:
			self.fail("Saldo suficiente no debería fallar")

	def test_validate_item_balance_blocks_negative(self) -> None:
		with self.assertRaises(PurchaseValidationError):
			validate_item_balance("ITEM-001", "WH-001", money("30"), money("100"))

	def test_stock_balance_add_and_remove(self) -> None:
		sb = StockBalance()
		sb.add("ITEM-A", "WH-1", money("100"))
		self.assertEqual(money("100"), sb.balance("ITEM-A", "WH-1"))
		sb.remove("ITEM-A", "WH-1", money("30"))
		self.assertEqual(money("70"), sb.balance("ITEM-A", "WH-1"))

	def test_stock_balance_insufficient_raises(self) -> None:
		sb = StockBalance()
		sb.add("ITEM-A", "WH-1", money("10"))
		with self.assertRaises(PurchaseValidationError):
			sb.remove("ITEM-A", "WH-1", money("20"))

	def test_stock_balance_returns_zero_for_missing(self) -> None:
		sb = StockBalance()
		self.assertEqual(money("0"), sb.balance("NONEXISTENT", "WH-1"))

	def test_stock_transaction_types_are_defined(self) -> None:
		from nexora.inventory.core import STOCK_TRANSACTION_TYPES

		for t in (
			"Receipt",
			"Transfer In",
			"Transfer Out",
			"Issue to Contractor",
			"Consumption",
			"Return",
			"Damage",
			"Loss",
			"Adjustment",
			"Physical Count",
		):
			self.assertIn(t, STOCK_TRANSACTION_TYPES)
