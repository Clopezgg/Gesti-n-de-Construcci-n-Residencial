from __future__ import annotations

import unittest

from nexora.purchases.request_core import (
	PurchaseValidationError,
	assert_request_transition,
	request_line_amounts,
	validate_request_dates,
)


class TestPurchaseRequestCore(unittest.TestCase):
	def test_multiline_amounts_are_exact(self) -> None:
		result = request_line_amounts(
			[
				{
					"line_code": "001",
					"item_type": "Goods",
					"description": "Cemento",
					"quantity": "3",
					"uom": "Bag",
					"estimated_unit_rate": "250.25",
					"estimated_amount": "750.75",
					"economic_category": "MATERIALS",
				},
				{
					"line_code": "002",
					"item_type": "Service",
					"description": "Transporte",
					"quantity": "1",
					"uom": "Nos",
					"estimated_unit_rate": "500",
					"estimated_amount": "500",
					"economic_category": "TRANSPORT",
				},
			]
		)
		self.assertEqual("1250.75", str(result.total))
		self.assertEqual(2, result.line_count)

	def test_duplicate_and_mismatched_lines_are_rejected(self) -> None:
		base = {
			"line_code": "001",
			"item_type": "Goods",
			"description": "Material",
			"quantity": "2",
			"uom": "Nos",
			"estimated_unit_rate": "10",
			"estimated_amount": "20",
			"economic_category": "MATERIALS",
		}
		with self.assertRaisesRegex(PurchaseValidationError, "duplicada"):
			request_line_amounts([base, base])
		with self.assertRaisesRegex(PurchaseValidationError, "no coincide"):
			request_line_amounts([{**base, "estimated_amount": "19.99"}])

	def test_request_dates_and_transitions_are_strict(self) -> None:
		validate_request_dates("2026-07-24", "2026-07-25")
		assert_request_transition("Draft", "In Review")
		assert_request_transition("In Review", "Approved")
		with self.assertRaisesRegex(PurchaseValidationError, "fecha requerida"):
			validate_request_dates("2026-07-25", "2026-07-24")
		with self.assertRaisesRegex(PurchaseValidationError, "Transición no permitida"):
			assert_request_transition("Approved", "Draft")


if __name__ == "__main__":
	unittest.main()
