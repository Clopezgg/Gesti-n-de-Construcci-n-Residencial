from __future__ import annotations

import unittest

from nexora.financial.catalog import ECONOMIC_CATEGORIES, OPERATION_PROFILES, apply_profile
from nexora.financial.core import FinancialError, SourceState, preview_operation
from nexora.financial.reference_rules import derive_reference_effects


class TestCentralLedgerCatalog(unittest.TestCase):
	def payload(self, code: str, category: str, amount: int = 100, **extra):
		data = {
			"operation_code": code,
			"economic_category": category,
			"project": "P1",
			"amount_hnl": amount,
			"allocations": [{"source": "F1", "amount_hnl": amount}],
			"requester": "requester@example.test",
			"approved_by": "manager@example.test",
			**extra,
		}
		return apply_profile(data, OPERATION_PROFILES[code], ECONOMIC_CATEGORIES[category])

	def original_effects(self) -> list[dict[str, object]]:
		return [
			{
				"name": "EFF-COST",
				"dimension": "Cost",
				"amount_hnl": 100,
				"remaining_hnl": 100,
				"project": "P1",
				"cost_center": "CC-1",
				"economic_category": "CONSTRUCTION_MATERIALS",
			},
			{
				"name": "EFF-BUDGET",
				"dimension": "Budget",
				"amount_hnl": 100,
				"remaining_hnl": 100,
				"project": "P1",
				"cost_center": "CC-1",
				"economic_category": "CONSTRUCTION_MATERIALS",
			},
		]

	def test_catalog_covers_required_real_operation_families(self):
		for code in (
			"MAXIMUM_ACCOUNT",
			"INTERNAL_TRANSFER",
			"OTHER_PROJECT",
			"LAND_PURCHASE",
			"OWNER_DEPOSIT",
			"GIFT_PAYMENT",
			"DONATION_PAYMENT",
			"CONTRIBUTION_PAYMENT",
			"TAX_PAYMENT",
			"LEGAL_PAYMENT",
			"TRAVEL_PAYMENT",
			"SPECIAL_PAYMENT",
			"ADVANCE_DISBURSEMENT",
			"ADVANCE_SETTLEMENT",
			"RECLASSIFICATION",
			"REAL_RETURN",
			"REVERSAL_NO_CASH",
			"DOCUMENT_SUBSTITUTION",
		):
			self.assertIn(code, OPERATION_PROFILES)

	def test_maximum_account_reduces_funds_and_increases_savings_not_cost(self):
		data = self.payload("MAXIMUM_ACCOUNT", "MAXIMUM_ACCOUNT")
		preview = preview_operation(data, {"F1": SourceState.from_values(500)})
		self.assertEqual("400.00", preview["sources"][0]["balance_after_hnl"])
		self.assertEqual("100.00", preview["savings_effect_hnl"])
		self.assertEqual("0.00", preview["cost_effect_hnl"])

	def test_internal_transfer_is_net_zero_and_uses_distinct_destination(self):
		data = self.payload(
			"INTERNAL_TRANSFER",
			"INTERNAL_TRANSFER",
			destination_source="F2",
			target_project="P2",
		)
		preview = preview_operation(
			data,
			{"F1": SourceState.from_values(500), "F2": SourceState.from_values(50)},
		)
		self.assertEqual(
			["Source", "Destination"],
			[row["allocation_role"] for row in preview["sources"]],
		)
		self.assertEqual("400.00", preview["sources"][0]["balance_after_hnl"])
		self.assertEqual("150.00", preview["sources"][1]["balance_after_hnl"])
		self.assertAlmostEqual(
			0.0,
			sum(float(row["funds_delta_hnl"]) for row in preview["sources"]),
		)

	def test_other_project_records_investment_on_target_project(self):
		data = self.payload(
			"OTHER_PROJECT",
			"OTHER_PROJECT",
			target_project="P2",
			reference_name="PROYECTO-2",
		)
		preview = preview_operation(data, {"F1": SourceState.from_values(500)})
		self.assertEqual("100.00", preview["investment_effect_hnl"])
		self.assertEqual("P2", preview["analytic_effects"][0]["project"])

	def test_advance_disbursement_requires_responsible_date_and_due_date(self):
		with self.assertRaisesRegex(FinancialError, "vencimiento"):
			self.payload(
				"ADVANCE_DISBURSEMENT",
				"ADVANCE",
				beneficiary="Supplier A",
				operation_date="2026-07-22",
			)
		data = self.payload(
			"ADVANCE_DISBURSEMENT",
			"ADVANCE",
			beneficiary="Supplier A",
			operation_date="2026-07-22",
			due_date="2026-08-22",
		)
		self.assertEqual("2026-08-22", data["due_date"])

	def test_advance_settlement_recognizes_cost_without_consuming_funds(self):
		data = self.payload(
			"ADVANCE_SETTLEMENT",
			"ADVANCE_SETTLEMENT",
			reference_name="ADV-1",
			cost_center="CC-1",
			allocations=[],
		)
		preview = preview_operation(data, {})
		self.assertEqual([], preview["sources"])
		self.assertEqual("100.00", preview["cost_effect_hnl"])
		self.assertEqual("0.00", preview["budget_effect_hnl"])

	def test_cost_center_divisions_must_sum_exactly(self):
		with self.assertRaisesRegex(FinancialError, "sumar"):
			self.payload(
				"CONSTRUCTION_PAYMENT",
				"CONSTRUCTION_MATERIALS",
				beneficiary="Supplier A",
				analytic_splits=[
					{"cost_center": "CC-1", "amount_hnl": 40},
					{"cost_center": "CC-2", "amount_hnl": 50},
				],
			)

	def test_reclassification_is_net_zero_and_has_no_funds(self):
		data = self.payload(
			"RECLASSIFICATION",
			"CONSTRUCTION_LABOR",
			reference_name="OP-1",
			cost_center="CC-2",
			allocations=[],
		)
		data["derived_analytic_effects"] = derive_reference_effects(
			100,
			100,
			self.original_effects(),
			mode="reclassification",
			target_category="CONSTRUCTION_LABOR",
			target_cost_center="CC-2",
		)
		preview = preview_operation(data, {})
		self.assertEqual([], preview["sources"])
		self.assertEqual("0.00", preview["cost_effect_hnl"])
		self.assertEqual("0.00", preview["budget_effect_hnl"])
		self.assertEqual(4, len(preview["analytic_effects"]))

	def test_reversal_without_cash_derives_dimensions_and_never_changes_funds(self):
		data = self.payload(
			"REVERSAL_NO_CASH",
			"REVERSAL",
			reference_name="OP-1",
			allocations=[],
		)
		data["derived_analytic_effects"] = derive_reference_effects(
			100,
			100,
			self.original_effects(),
			mode="reversal",
		)
		preview = preview_operation(data, {})
		self.assertEqual([], preview["sources"])
		self.assertEqual("-100.00", preview["cost_effect_hnl"])
		self.assertEqual("-100.00", preview["budget_effect_hnl"])

	def test_special_payment_requires_authorizer_method_date_and_reference(self):
		with self.assertRaisesRegex(FinancialError, "fecha"):
			self.payload(
				"SPECIAL_PAYMENT",
				"SPECIAL",
				beneficiary="Supplier A",
				evidence="/private/files/x.pdf",
				cost_center="CC-1",
				payment_method="Transfer",
				external_reference="REF-1",
			)
		data = self.payload(
			"SPECIAL_PAYMENT",
			"SPECIAL",
			beneficiary="Supplier A",
			evidence="/private/files/x.pdf",
			cost_center="CC-1",
			payment_method="Transfer",
			external_reference="REF-1",
			operation_date="2026-07-22",
		)
		self.assertEqual("Transfer", data["payment_method"])

	def test_document_substitution_requires_zero_amount_and_evidence(self):
		with self.assertRaises(FinancialError):
			self.payload(
				"DOCUMENT_SUBSTITUTION",
				"DOCUMENTARY",
				reference_name="OP-1",
				evidence="/x.pdf",
			)
		data = self.payload(
			"DOCUMENT_SUBSTITUTION",
			"DOCUMENTARY",
			amount=0,
			reference_name="OP-1",
			evidence="/private/files/new.pdf",
			allocations=[],
		)
		self.assertEqual("Reclassification", data["operation_type"])


if __name__ == "__main__":
	unittest.main()
