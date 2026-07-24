from __future__ import annotations

import unittest
from decimal import Decimal

from nexora.contracts.core import (
    AMENDMENT_TRANSITIONS,
    CONTRACT_TRANSITIONS,
    amendment_balances,
    assert_transition,
    ensure_available,
    estimate_amounts,
    line_amounts,
    money,
    validate_amendment,
    validate_period,
)


class TestContractCore(unittest.TestCase):
    def test_line_amounts_separate_labor_and_materials(self) -> None:
        result = line_amounts([
            {"line_code": "L", "quantity": 2, "unit_rate": 100, "amount": 200, "cost_kind": "Labor"},
            {"line_code": "M", "quantity": 3, "unit_rate": 50, "amount": 150, "cost_kind": "Materials"},
        ])
        self.assertEqual(Decimal("200.00"), result.labor)
        self.assertEqual(Decimal("150.00"), result.materials)
        self.assertEqual(Decimal("350.00"), result.total)

    def test_line_amounts_reject_duplicates_and_mismatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicada"):
            line_amounts([
                {"line_code": "A", "quantity": 1, "unit_rate": 10, "amount": 10, "cost_kind": "Labor"},
                {"line_code": "A", "quantity": 1, "unit_rate": 10, "amount": 10, "cost_kind": "Labor"},
            ])
        with self.assertRaisesRegex(ValueError, "no coincide"):
            line_amounts([{"line_code": "A", "quantity": 2, "unit_rate": 10, "amount": 19, "cost_kind": "Labor"}])

    def test_estimate_amounts_concile_manual_deductions(self) -> None:
        result = estimate_amounts(1000, 100, 50, 25, 25)
        self.assertEqual(Decimal("800.00"), result.payable)
        with self.assertRaisesRegex(ValueError, "superar"):
            estimate_amounts(100, 50, 30, 20, 10)

    def test_amendment_cannot_reduce_below_execution(self) -> None:
        result = amendment_balances(1000, 500, -200, 100, 700, 200)
        self.assertEqual(Decimal("800.00"), result.labor)
        self.assertEqual(Decimal("600.00"), result.materials)
        with self.assertRaisesRegex(ValueError, "debajo"):
            amendment_balances(1000, 500, -400, 0, 700, 100)

    def test_transitions_and_periods_are_strict(self) -> None:
        assert_transition("Draft", "In Review", CONTRACT_TRANSITIONS)
        assert_transition("Draft", "In Review", AMENDMENT_TRANSITIONS)
        with self.assertRaisesRegex(ValueError, "no permitida"):
            assert_transition("Draft", "Liquidated", CONTRACT_TRANSITIONS)
        validate_period("2026-01-01", "2026-12-31")
        with self.assertRaisesRegex(ValueError, "anterior"):
            validate_period("2026-12-31", "2026-01-01")

    def test_available_and_money_are_exact(self) -> None:
        self.assertEqual(Decimal("10.01"), money("10.005"))
        ensure_available(10, 10, "de prueba")
        with self.assertRaisesRegex(ValueError, "excede"):
            ensure_available(11, 10, "de prueba")

    def test_amendment_types_enforce_signs_dates_and_status(self) -> None:
        validate_amendment("Increase", labor_delta=100, current_status="Active")
        validate_amendment("Reduction", labor_delta=-100, current_status="Active")
        validate_amendment(
            "Extension", current_status="Active", current_end_date="2026-12-31", new_end_date="2027-01-01"
        )
        validate_amendment("Suspension", current_status="Active")
        validate_amendment("Reactivation", current_status="Suspended")
        with self.assertRaisesRegex(ValueError, "incremento"):
            validate_amendment("Increase", labor_delta=-1, current_status="Active")
        with self.assertRaisesRegex(ValueError, "disminución"):
            validate_amendment("Reduction", labor_delta=1, current_status="Active")
        with self.assertRaisesRegex(ValueError, "posterior"):
            validate_amendment(
                "Extension", current_status="Active", current_end_date="2026-12-31", new_end_date="2026-12-31"
            )
        with self.assertRaisesRegex(ValueError, "suspendido"):
            validate_amendment("Reactivation", current_status="Active")


if __name__ == "__main__":
    unittest.main()
