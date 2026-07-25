from __future__ import annotations

from decimal import Decimal
from unittest import TestCase

from nexora.progress.core import (
	PROGRESS_TRANSITIONS,
	InvalidTransition,
	ProgressValidationError,
	assert_transition,
	money,
	progress_percent,
)


class TestProgressCore(TestCase):
	def test_draft_can_be_submitted(self) -> None:
		try:
			assert_transition("Draft", "Submitted")
		except InvalidTransition:
			self.fail("Draft -> Submitted debería ser válido")

	def test_draft_can_be_cancelled(self) -> None:
		try:
			assert_transition("Draft", "Cancelled")
		except InvalidTransition:
			self.fail("Draft -> Cancelled debería ser válido")

	def test_submitted_can_be_approved(self) -> None:
		try:
			assert_transition("Submitted", "Approved")
		except InvalidTransition:
			self.fail("Submitted -> Approved debería ser válido")

	def test_submitted_can_be_rejected(self) -> None:
		try:
			assert_transition("Submitted", "Rejected")
		except InvalidTransition:
			self.fail("Submitted -> Rejected debería ser válido")

	def test_approved_can_be_corrected(self) -> None:
		try:
			assert_transition("Approved", "Corrected")
		except InvalidTransition:
			self.fail("Approved -> Corrected debería ser válido")

	def test_corrected_can_be_approved(self) -> None:
		try:
			assert_transition("Corrected", "Approved")
		except InvalidTransition:
			self.fail("Corrected -> Approved debería ser válido")

	def test_rejected_can_be_corrected(self) -> None:
		try:
			assert_transition("Rejected", "Corrected")
		except InvalidTransition:
			self.fail("Rejected -> Corrected debería ser válido")

	def test_cancelled_has_no_outgoing(self) -> None:
		allowed = PROGRESS_TRANSITIONS.get("Cancelled")
		self.assertIsNotNone(allowed)
		self.assertEqual(0, len(allowed))

	def test_unknown_state_is_rejected(self) -> None:
		with self.assertRaises(InvalidTransition):
			assert_transition("Unknown", "Draft")

	def test_invalid_transition_raises(self) -> None:
		with self.assertRaises(InvalidTransition):
			assert_transition("Cancelled", "Submitted")

	def test_invalid_direct_approval_raises(self) -> None:
		with self.assertRaises(InvalidTransition):
			assert_transition("Draft", "Approved")

	def test_all_states_have_transitions(self) -> None:
		for state, targets in PROGRESS_TRANSITIONS.items():
			for target in targets:
				try:
					assert_transition(state, target)
				except InvalidTransition:
					self.fail(f"{state} -> {target} debería ser válido")

	def test_terminal_states_contains_cancelled(self) -> None:
		from nexora.progress.core import TERMINAL_STATES

		self.assertIn("Cancelled", TERMINAL_STATES)

	def test_money_rounds_half_up(self) -> None:
		result = money("1.235")
		self.assertEqual(Decimal("1.24"), result)

	def test_money_rounds_half_down(self) -> None:
		result = money("1.234")
		self.assertEqual(Decimal("1.23"), result)

	def test_money_zero(self) -> None:
		result = money(0)
		self.assertEqual(Decimal("0.00"), result)

	def test_money_negative(self) -> None:
		result = money("-50.50")
		self.assertEqual(Decimal("-50.50"), result)

	def test_money_invalid_raises(self) -> None:
		with self.assertRaises(ProgressValidationError):
			money("not_a_number")

	def test_progress_percent_zero(self) -> None:
		result = progress_percent(0)
		self.assertEqual(Decimal(0), result)

	def test_progress_percent_fifty(self) -> None:
		result = progress_percent(50)
		self.assertEqual(Decimal(50), result)

	def test_progress_percent_one_hundred(self) -> None:
		result = progress_percent(100)
		self.assertEqual(Decimal(100), result)

	def test_progress_percent_negative_raises(self) -> None:
		with self.assertRaises(ProgressValidationError):
			progress_percent(-1)

	def test_progress_percent_over_one_hundred_raises(self) -> None:
		with self.assertRaises(ProgressValidationError):
			progress_percent(101)

	def test_progress_percent_invalid_raises(self) -> None:
		with self.assertRaises(ProgressValidationError):
			progress_percent("not_a_number")
