from __future__ import annotations

import unittest
from decimal import Decimal

from nexora.financial.core import FinancialError
from nexora.financial.reference_rules import (
	SEGREGATED_OPERATION_CODES,
	available_amount_from_effects,
	bounded_reference_amount,
	derive_reference_effects,
	validate_advance_dates,
	validate_return_allocations,
	validate_segregation,
)


class TestReferenceRules(unittest.TestCase):
	def effects(self, remaining: int = 1000) -> list[dict[str, object]]:
		return [
			{
				"name": "EFF-COST",
				"dimension": "Cost",
				"amount_hnl": 1000,
				"remaining_hnl": remaining,
				"project": "P1",
				"cost_center": "CC-OLD",
				"economic_category": "CONSTRUCTION_MATERIALS",
			},
			{
				"name": "EFF-BUDGET",
				"dimension": "Budget",
				"amount_hnl": 1000,
				"remaining_hnl": remaining,
				"project": "P1",
				"cost_center": "CC-OLD",
				"economic_category": "CONSTRUCTION_MATERIALS",
			},
		]

	def test_reclassification_generates_negative_old_and_positive_new_effects(self) -> None:
		rows = derive_reference_effects(
			1000,
			400,
			self.effects(),
			mode="reclassification",
			target_category="CONSTRUCTION_LABOR",
			target_cost_center="CC-NEW",
		)
		self.assertEqual(4, len(rows))
		for dimension in ("Cost", "Budget"):
			dimension_rows = [row for row in rows if row["dimension"] == dimension]
			self.assertEqual(Decimal("0.00"), sum(Decimal(row["amount_hnl"]) for row in dimension_rows))
			negative = next(row for row in dimension_rows if Decimal(row["amount_hnl"]) < 0)
			positive = next(row for row in dimension_rows if Decimal(row["amount_hnl"]) > 0)
			self.assertEqual("CONSTRUCTION_MATERIALS", negative["economic_category"])
			self.assertEqual("CONSTRUCTION_LABOR", positive["economic_category"])
			self.assertEqual("CC-OLD", negative["cost_center"])
			self.assertEqual("CC-NEW", positive["cost_center"])
			self.assertEqual("P1", negative["project"])
			self.assertEqual("P1", positive["project"])
			self.assertTrue(negative["reverses_effect"])

	def test_reclassification_is_limited_by_effect_balance(self) -> None:
		self.assertEqual(Decimal("600.00"), available_amount_from_effects(1000, self.effects(600)))
		derive_reference_effects(
			1000,
			600,
			self.effects(600),
			mode="reclassification",
			target_category="CONSTRUCTION_LABOR",
		)
		with self.assertRaisesRegex(FinancialError, "disponible"):
			derive_reference_effects(
				1000,
				601,
				self.effects(600),
				mode="reclassification",
				target_category="CONSTRUCTION_LABOR",
			)

	def test_reversal_derives_original_dimensions_without_funds(self) -> None:
		rows = derive_reference_effects(1000, 250, self.effects(), mode="reversal")
		self.assertEqual({"Cost", "Budget"}, {row["dimension"] for row in rows})
		self.assertTrue(all(Decimal(row["amount_hnl"]) == Decimal("-250.00") for row in rows))
		self.assertTrue(all(row["project"] == "P1" for row in rows))
		self.assertTrue(all(row["cost_center"] == "CC-OLD" for row in rows))
		self.assertNotIn("Funds", {row["dimension"] for row in rows})

	def test_real_return_supports_partial_same_source_and_explicit_relation(self) -> None:
		rows, requested, available = validate_return_allocations(
			{"SRC-A": 600, "SRC-B": 400},
			{"SRC-A": 100},
			[
				{"source": "SRC-A", "amount_hnl": 200},
				{"source": "SRC-C", "original_source": "SRC-B", "amount_hnl": 150},
			],
		)
		self.assertEqual(Decimal("350.00"), requested)
		self.assertEqual(Decimal("900.00"), available)
		self.assertEqual("SRC-B", rows[1]["related_source"])

	def test_real_return_blocks_duplicate_original_source_and_excess(self) -> None:
		with self.assertRaisesRegex(FinancialError, "repetida"):
			validate_return_allocations(
				{"SRC-A": 600},
				{},
				[
					{"source": "SRC-A", "amount_hnl": 100},
					{"source": "SRC-C", "original_source": "SRC-A", "amount_hnl": 100},
				],
			)
		with self.assertRaisesRegex(FinancialError, "recuperable"):
			validate_return_allocations(
				{"SRC-A": 600},
				{"SRC-A": 500},
				[{"source": "SRC-A", "amount_hnl": 101}],
			)

	def test_advance_balance_prevents_duplicate_or_excessive_settlement(self) -> None:
		partial = bounded_reference_amount(1000, 400, 300, label="de liquidación")
		self.assertEqual(Decimal("300.00"), partial.remaining)
		full = bounded_reference_amount(1000, 700, None, label="de liquidación")
		self.assertEqual(Decimal("300.00"), full.requested)
		with self.assertRaisesRegex(FinancialError, "supera"):
			bounded_reference_amount(1000, 700, 301, label="de liquidación")
		with self.assertRaisesRegex(FinancialError, "mayor que cero"):
			bounded_reference_amount(1000, 1000, None, label="de liquidación")

	def test_advance_requires_valid_date_and_due_date(self) -> None:
		validate_advance_dates("2026-07-22", "2026-08-22")
		with self.assertRaisesRegex(FinancialError, "anterior"):
			validate_advance_dates("2026-07-22", "2026-07-21")

	def test_segregation_applies_to_every_required_profile(self) -> None:
		expected = {
			"INTERNAL_TRANSFER",
			"ADVANCE_DISBURSEMENT",
			"ADVANCE_SETTLEMENT",
			"RECLASSIFICATION",
			"REAL_RETURN",
			"REVERSAL_NO_CASH",
			"DOCUMENT_SUBSTITUTION",
		}
		self.assertEqual(expected, set(SEGREGATED_OPERATION_CODES))
		validate_segregation("requester", "approver", "executor")
		with self.assertRaisesRegex(FinancialError, "tres usuarios distintos"):
			validate_segregation("requester", "approver", "approver")


if __name__ == "__main__":
	unittest.main()
