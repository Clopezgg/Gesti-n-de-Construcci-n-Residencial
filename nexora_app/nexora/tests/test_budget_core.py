from __future__ import annotations

from decimal import Decimal
from unittest import TestCase

from nexora.budget.core import (
	BUDGET_TRANSITIONS,
	InvalidLineError,
	InvalidTransition,
	OverspendError,
	assert_transition,
	compute_budget_totals,
	compute_line_balances,
	validate_line_amount,
	validate_no_overspend,
)


class TestBudgetCore(TestCase):
	def test_draft_can_be_activated(self) -> None:
		try:
			assert_transition("Draft", "Active")
		except InvalidTransition:
			self.fail("Draft -> Active debería ser válido")

	def test_draft_can_be_cancelled(self) -> None:
		try:
			assert_transition("Draft", "Cancelled")
		except InvalidTransition:
			self.fail("Draft -> Cancelled debería ser válido")

	def test_active_can_be_amended(self) -> None:
		try:
			assert_transition("Active", "Amended")
		except InvalidTransition:
			self.fail("Active -> Amended debería ser válido")

	def test_active_can_be_closed(self) -> None:
		try:
			assert_transition("Active", "Closed")
		except InvalidTransition:
			self.fail("Active -> Closed debería ser válido")

	def test_terminal_states_have_no_outgoing(self) -> None:
		for state in ("Amended", "Closed", "Cancelled"):
			allowed = BUDGET_TRANSITIONS.get(state)
			self.assertIsNotNone(allowed)
			self.assertEqual(0, len(allowed))

	def test_unknown_state_is_rejected(self) -> None:
		with self.assertRaises(InvalidTransition):
			assert_transition("Unknown", "Draft")

	def test_invalid_transition_raises(self) -> None:
		with self.assertRaises(InvalidTransition):
			assert_transition("Cancelled", "Active")

	def test_all_states_have_transitions(self) -> None:
		for state, targets in BUDGET_TRANSITIONS.items():
			for target in targets:
				try:
					assert_transition(state, target)
				except InvalidTransition:
					self.fail(f"{state} -> {target} debería ser válido")

	def test_compute_line_balances(self) -> None:
		bal = compute_line_balances("1000", "300", "100")
		self.assertEqual(Decimal("1000.00"), bal["approved_hnl"])
		self.assertEqual(Decimal("300.00"), bal["committed_hnl"])
		self.assertEqual(Decimal("100.00"), bal["executed_hnl"])
		self.assertEqual(Decimal("600.00"), bal["available_hnl"])

	def test_compute_line_balances_zero(self) -> None:
		bal = compute_line_balances("0", "0", "0")
		self.assertEqual(Decimal("0.00"), bal["available_hnl"])

	def test_compute_line_balances_fully_consumed(self) -> None:
		bal = compute_line_balances("500", "500", "0")
		self.assertEqual(Decimal("0.00"), bal["available_hnl"])

	def test_overspend_raises(self) -> None:
		with self.assertRaises(OverspendError):
			validate_no_overspend("1000", "300", "100", "800")

	def test_overspend_at_exact_boundary(self) -> None:
		with self.assertRaises(OverspendError):
			validate_no_overspend("1000", "300", "100", "601")

	def test_valid_commitment_passes(self) -> None:
		try:
			validate_no_overspend("1000", "300", "100", "500")
		except OverspendError:
			self.fail("Compromiso dentro del disponible no debería fallar")

	def test_valid_commitment_exact_available(self) -> None:
		try:
			validate_no_overspend("1000", "300", "100", "600")
		except OverspendError:
			self.fail("Compromiso exacto al disponible no debería fallar")

	def test_validate_line_amount_positive(self) -> None:
		result = validate_line_amount("500")
		self.assertEqual(Decimal("500.00"), result)

	def test_validate_line_amount_zero_raises(self) -> None:
		with self.assertRaises(InvalidLineError):
			validate_line_amount("0")

	def test_validate_line_amount_negative_raises(self) -> None:
		with self.assertRaises(InvalidLineError):
			validate_line_amount("-100")

	def test_compute_budget_totals(self) -> None:
		lines = [
			{"approved_hnl": "1000", "committed_hnl": "300", "executed_hnl": "100"},
			{"approved_hnl": "2000", "committed_hnl": "500", "executed_hnl": "200"},
		]
		totals = compute_budget_totals(lines)
		self.assertEqual(Decimal("3000.00"), totals["total_approved_hnl"])
		self.assertEqual(Decimal("800.00"), totals["total_committed_hnl"])
		self.assertEqual(Decimal("300.00"), totals["total_executed_hnl"])
		self.assertEqual(Decimal("1900.00"), totals["total_available_hnl"])
