from __future__ import annotations

from unittest import TestCase

from nexora.close.core import (
	CLOSE_TRANSITIONS,
	TERMINAL_STATES,
	InvalidTransition,
	ReconciliationError,
	assert_transition,
	reconcile,
)


class TestCloseCore(TestCase):
	def test_draft_to_in_review(self) -> None:
		try:
			assert_transition("Draft", "In Review")
		except InvalidTransition:
			self.fail("Draft -> In Review deberia ser valido")

	def test_draft_to_cancelled(self) -> None:
		try:
			assert_transition("Draft", "Cancelled")
		except InvalidTransition:
			self.fail("Draft -> Cancelled deberia ser valido")

	def test_in_review_to_approved(self) -> None:
		try:
			assert_transition("In Review", "Approved")
		except InvalidTransition:
			self.fail("In Review -> Approved deberia ser valido")

	def test_in_review_to_rejected(self) -> None:
		try:
			assert_transition("In Review", "Rejected")
		except InvalidTransition:
			self.fail("In Review -> Rejected deberia ser valido")

	def test_rejected_to_draft(self) -> None:
		try:
			assert_transition("Rejected", "Draft")
		except InvalidTransition:
			self.fail("Rejected -> Draft deberia ser valido")

	def test_terminal_states_have_no_outgoing(self) -> None:
		for state in ("Approved", "Cancelled"):
			allowed = CLOSE_TRANSITIONS.get(state)
			self.assertIsNotNone(allowed)
			self.assertEqual(0, len(allowed))

	def test_approved_is_terminal(self) -> None:
		self.assertIn("Approved", TERMINAL_STATES)

	def test_cancelled_is_terminal(self) -> None:
		self.assertIn("Cancelled", TERMINAL_STATES)

	def test_invalid_transition_raises(self) -> None:
		with self.assertRaises(InvalidTransition):
			assert_transition("Draft", "Approved")

	def test_unknown_state_raises(self) -> None:
		with self.assertRaises(InvalidTransition):
			assert_transition("Unknown", "Draft")

	def test_reconcile_passes_with_equal_values(self) -> None:
		before = {"total_inflows_hnl": 1000, "total_outflows_hnl": 500}
		after = {"total_inflows_hnl": 1000, "total_outflows_hnl": 500}
		result = reconcile(before, after)
		self.assertEqual(1000, result["total_inflows_hnl"])
		self.assertEqual(500, result["total_outflows_hnl"])

	def test_reconcile_passes_with_empty_dicts(self) -> None:
		result = reconcile({}, {})
		self.assertEqual({}, result)

	def test_reconcile_raises_with_mismatched_values(self) -> None:
		before = {"total_inflows_hnl": 1000, "total_outflows_hnl": 500}
		after = {"total_inflows_hnl": 900, "total_outflows_hnl": 500}
		with self.assertRaises(ReconciliationError):
			reconcile(before, after)

	def test_reconcile_raises_with_missing_key(self) -> None:
		before = {"total_inflows_hnl": 1000}
		after = {}
		with self.assertRaises(ReconciliationError):
			reconcile(before, after)
