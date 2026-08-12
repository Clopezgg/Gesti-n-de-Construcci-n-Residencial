from __future__ import annotations

from unittest import TestCase

from nexora.quality.core import (
	QUALITY_TRANSITIONS,
	InvalidTransition,
	QualityValidationError,
	assert_transition,
	assert_valid_result,
)


class TestQualityCore(TestCase):
	def test_open_can_be_passed(self) -> None:
		try:
			assert_transition("Open", "Passed")
		except InvalidTransition:
			self.fail("Open -> Passed debería ser válido")

	def test_open_can_be_failed(self) -> None:
		try:
			assert_transition("Open", "Failed")
		except InvalidTransition:
			self.fail("Open -> Failed debería ser válido")

	def test_failed_can_be_corrected(self) -> None:
		try:
			assert_transition("Failed", "Corrected")
		except InvalidTransition:
			self.fail("Failed -> Corrected debería ser válido")

	def test_corrected_can_be_passed_or_failed_again(self) -> None:
		try:
			assert_transition("Corrected", "Passed")
			assert_transition("Corrected", "Failed")
		except InvalidTransition:
			self.fail("Corrected -> Passed/Failed debería ser válido")

	def test_passed_can_be_closed(self) -> None:
		try:
			assert_transition("Passed", "Closed")
		except InvalidTransition:
			self.fail("Passed -> Closed debería ser válido")

	def test_closed_has_no_outgoing(self) -> None:
		allowed = QUALITY_TRANSITIONS.get("Closed")
		self.assertEqual(frozenset(), allowed)

	def test_open_cannot_jump_directly_to_closed(self) -> None:
		with self.assertRaises(InvalidTransition):
			assert_transition("Open", "Closed")

	def test_failed_cannot_jump_directly_to_passed(self) -> None:
		with self.assertRaises(InvalidTransition):
			assert_transition("Failed", "Passed")

	def test_unknown_state_is_rejected(self) -> None:
		with self.assertRaises(InvalidTransition):
			assert_transition("NotAState", "Passed")

	def test_valid_result_values_are_accepted(self) -> None:
		for value in ("Pass", "Fail", "Not Tested", ""):
			self.assertEqual(value, assert_valid_result(value))

	def test_invalid_result_is_rejected(self) -> None:
		with self.assertRaises(QualityValidationError):
			assert_valid_result("Maybe")


if __name__ == "__main__":
	import unittest

	unittest.main()
