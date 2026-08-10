from __future__ import annotations

import unittest

from nexora.dashboard.analytics_core import (
	classify_effect,
	normalize_period,
	stable_payload_hash,
	summarize_effect_rows,
)


class TestExecutiveAnalytics(unittest.TestCase):
	def test_period_rejects_inverted_dates(self) -> None:
		with self.assertRaisesRegex(ValueError, "fecha final"):
			normalize_period("2026-07-08", "2026-07-01")

	def test_period_accepts_a_partial_month_free_range(self) -> None:
		# El motivo de esta prueba: el 01-30 de julio (excluye el día 31) no es un mes
		# calendario completo. El selector del dashboard solo ofrece meses completos
		# (ver `_period_bounds` en boot.py), pero el motor analítico que consume tanto el
		# dashboard como el centro de reportes no tiene esa restricción: acepta cualquier
		# rango válido. Esto confirma que la limitación es del control de UI del
		# dashboard, no del backend ni del centro de reportes.
		start, end = normalize_period("2026-07-01", "2026-07-30")
		self.assertEqual((start, end), ("2026-07-01", "2026-07-30"))

	def test_period_accepts_an_empty_range_as_unbounded(self) -> None:
		start, end = normalize_period(None, None)
		self.assertEqual(start, "1900-01-01")
		self.assertEqual(end, "9999-12-31")

	def test_internal_transfer_does_not_become_expense(self) -> None:
		rows = [
			{
				"fund_source": "A",
				"operation_date": "2026-07-02",
				"operation_type": "Inflow",
				"dimension": "Funds",
				"amount_hnl": 100,
			},
			{
				"fund_source": "A",
				"operation_date": "2026-07-04",
				"operation_type": "Internal Transfer",
				"dimension": "Funds",
				"amount_hnl": -30,
			},
			{
				"fund_source": "B",
				"operation_date": "2026-07-04",
				"operation_type": "Internal Transfer",
				"dimension": "Funds",
				"amount_hnl": 30,
			},
		]
		result = summarize_effect_rows(rows, from_date="2026-07-01", to_date="2026-07-07")
		self.assertEqual(30, result["A"]["transfer_out_hnl"])
		self.assertEqual(30, result["B"]["transfer_in_hnl"])
		self.assertNotIn("spent_hnl", result["A"])
		self.assertEqual(70, result["A"]["closing_funds_hnl"])
		self.assertEqual(30, result["B"]["closing_funds_hnl"])

	def test_as_of_balances_separate_opening_closing_and_current(self) -> None:
		rows = [
			{
				"fund_source": "A",
				"operation_date": "2026-06-30",
				"operation_type": "Inflow",
				"dimension": "Funds",
				"amount_hnl": 100,
			},
			{
				"fund_source": "A",
				"operation_date": "2026-07-03",
				"operation_type": "Outflow",
				"dimension": "Funds",
				"amount_hnl": -25,
			},
			{
				"fund_source": "A",
				"operation_date": "2026-07-04",
				"operation_type": "Commitment Reserve",
				"dimension": "Reserved",
				"amount_hnl": 20,
			},
			{
				"fund_source": "A",
				"operation_date": "2026-07-20",
				"operation_type": "Outflow",
				"dimension": "Funds",
				"amount_hnl": -10,
			},
		]
		values = summarize_effect_rows(rows, from_date="2026-07-01", to_date="2026-07-07")["A"]
		self.assertEqual(100, values["opening_funds_hnl"])
		self.assertEqual(75, values["closing_funds_hnl"])
		self.assertEqual(55, values["closing_available_hnl"])
		self.assertEqual(65, values["current_funds_hnl"])
		self.assertEqual(45, values["current_available_hnl"])

	def test_reversal_is_explicit_and_preserves_received_history(self) -> None:
		rows = [
			{
				"fund_source": "A",
				"operation_date": "2026-07-01",
				"operation_type": "Inflow",
				"dimension": "Funds",
				"amount_hnl": 100,
				"is_reversal": 0,
			},
			{
				"fund_source": "A",
				"operation_date": "2026-07-02",
				"operation_type": "Analytic Adjustment",
				"dimension": "Funds",
				"amount_hnl": -100,
				"is_reversal": 1,
			},
		]
		values = summarize_effect_rows(rows, from_date="2026-07-01", to_date="2026-07-07")["A"]
		self.assertEqual(100, values["received_hnl"])
		self.assertEqual(100, values["reversed_hnl"])
		self.assertEqual(0, values["closing_funds_hnl"])
		self.assertEqual("reversed", classify_effect("Inflow", "Funds", -1, "1"))
		self.assertEqual("received", classify_effect("Inflow", "Funds", 1, "0"))

	def test_payload_hash_is_order_independent(self) -> None:
		self.assertEqual(stable_payload_hash({"a": 1, "b": 2}), stable_payload_hash({"b": 2, "a": 1}))


if __name__ == "__main__":
	unittest.main()
