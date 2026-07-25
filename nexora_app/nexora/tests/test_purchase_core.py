from __future__ import annotations

import unittest

from nexora.purchases.core import (
	SUPPLIER_PROFILE_TRANSITIONS,
	assert_transition,
	normalize_classification,
)


class TestPurchaseCore(unittest.TestCase):
	def test_supplier_classification_is_normalized(self) -> None:
		self.assertEqual("Goods", normalize_classification("goods"))
		self.assertEqual("Other", normalize_classification(None))

	def test_unknown_supplier_classification_is_rejected(self) -> None:
		with self.assertRaisesRegex(ValueError, "clasificación"):
			normalize_classification("Parallel Vendor")

	def test_supplier_profile_transitions_are_closed(self) -> None:
		assert_transition("Draft", "Active", SUPPLIER_PROFILE_TRANSITIONS)
		assert_transition("Active", "Suspended", SUPPLIER_PROFILE_TRANSITIONS)
		with self.assertRaisesRegex(ValueError, "Transición no permitida"):
			assert_transition("Inactive", "Active", SUPPLIER_PROFILE_TRANSITIONS)


if __name__ == "__main__":
	unittest.main()
