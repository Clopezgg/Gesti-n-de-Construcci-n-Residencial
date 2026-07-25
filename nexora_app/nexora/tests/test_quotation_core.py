from __future__ import annotations

import unittest

from nexora.purchases.quotation_core import (
	assert_quotation_transition,
)


class TestQuotationCore(unittest.TestCase):
	def test_draft_can_be_submitted(self) -> None:
		assert_quotation_transition("Draft", "Submitted")

	def test_draft_can_be_cancelled(self) -> None:
		assert_quotation_transition("Draft", "Cancelled")

	def test_submitted_can_be_accepted(self) -> None:
		assert_quotation_transition("Submitted", "Accepted")

	def test_accepted_is_terminal(self) -> None:
		assert_quotation_transition("Accepted", "Cancelled")

	def test_rejected_can_be_cancelled(self) -> None:
		assert_quotation_transition("Rejected", "Cancelled")

	def test_expired_is_terminal(self) -> None:
		with self.assertRaises(ValueError):
			assert_quotation_transition("Expired", "Submitted")

	def test_direct_acceptance_is_rejected(self) -> None:
		with self.assertRaises(ValueError):
			assert_quotation_transition("Draft", "Accepted")

	def test_rejected_cannot_be_accepted(self) -> None:
		with self.assertRaises(ValueError):
			assert_quotation_transition("Rejected", "Accepted")


if __name__ == "__main__":
	unittest.main()
