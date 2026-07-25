from __future__ import annotations

from decimal import Decimal
from unittest import TestCase

from nexora.reports.core import format_statement_rows, money, reconcile_amounts


class TestReportsCore(TestCase):
	def test_money_rounds_to_two_decimals(self) -> None:
		self.assertEqual(Decimal("150.00"), money("150"))
		self.assertEqual(Decimal("150.25"), money("150.25"))
		self.assertEqual(Decimal("150.26"), money("150.256"))

	def test_money_rejects_invalid(self) -> None:
		with self.assertRaises(ValueError):
			money("not-a-number")

	def test_reconcile_amounts_all_inflows(self) -> None:
		ops = [
			{"operation_type": "Inflow", "amount_hnl": "1000"},
			{"operation_type": "Inflow", "amount_hnl": "500"},
		]
		result = reconcile_amounts(ops)
		self.assertEqual(Decimal("1500.00"), result["total_inflows"])
		self.assertEqual(Decimal("0.00"), result["total_outflows"])
		self.assertEqual(Decimal("1500.00"), result["net_flow"])

	def test_reconcile_amounts_mixed(self) -> None:
		ops = [
			{"operation_type": "Inflow", "amount_hnl": "2000"},
			{"operation_type": "Outflow", "amount_hnl": "800"},
			{"operation_type": "Commitment Execution", "amount_hnl": "200"},
		]
		result = reconcile_amounts(ops)
		self.assertEqual(Decimal("2000.00"), result["total_inflows"])
		self.assertEqual(Decimal("1000.00"), result["total_outflows"])
		self.assertEqual(Decimal("1000.00"), result["net_flow"])

	def test_reconcile_real_return_included(self) -> None:
		ops = [
			{"operation_type": "Inflow", "amount_hnl": "1000"},
			{"operation_type": "Real Return", "amount_hnl": "300"},
		]
		result = reconcile_amounts(ops)
		self.assertEqual(Decimal("1300.00"), result["total_inflows"])

	def test_reconcile_empty(self) -> None:
		result = reconcile_amounts([])
		self.assertEqual(Decimal("0.00"), result["total_inflows"])
		self.assertEqual(Decimal("0.00"), result["total_outflows"])
		self.assertEqual(Decimal("0.00"), result["net_flow"])
		self.assertEqual(Decimal("0.00"), result["operation_count"])

	def test_format_statement_rows_running_balance(self) -> None:
		rows = [
			{
				"operation_type": "Inflow",
				"amount_hnl": "1000",
				"creation": "2026-01-01",
				"document_number": "OP-001",
				"status": "Executed",
				"description": "Ingreso inicial",
			},
			{
				"operation_type": "Outflow",
				"amount_hnl": "300",
				"creation": "2026-01-15",
				"document_number": "OP-002",
				"status": "Executed",
				"description": "Pago",
			},
		]
		formatted = format_statement_rows(rows)
		self.assertEqual(2, len(formatted))
		self.assertEqual(money("1000.00"), formatted[0]["running_balance"])
		self.assertEqual(money("700.00"), formatted[1]["running_balance"])

	def test_format_statement_rows_empty(self) -> None:
		self.assertEqual([], format_statement_rows([]))
