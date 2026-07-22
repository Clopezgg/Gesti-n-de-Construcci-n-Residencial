from __future__ import annotations

import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from nexora.financial.core import (
    AllocationMismatch,
    AtomicLedger,
    FinancialError,
    IdempotencyConflict,
    InsufficientFunds,
    SourceState,
    preview_operation,
    validate_source_payload,
)


class TestFinancialCore(unittest.TestCase):
    def test_01_create_hnl_remittance(self) -> None:
        result = validate_source_payload({"channel": "Remittance", "original_amount": "1000", "exchange_rate": 1})
        self.assertEqual("1000.00", result["amount_hnl"])

    def test_02_foreign_currency_conversion(self) -> None:
        result = validate_source_payload({"channel": "Remittance", "original_amount": "100", "exchange_rate": "24.500000000"})
        self.assertEqual("2450.00", result["amount_hnl"])
        self.assertEqual("24.500000000", result["exchange_rate"])

    def test_03_cash_does_not_require_bank(self) -> None:
        result = validate_source_payload({"channel": "Cash", "original_amount": "500", "exchange_rate": 1})
        self.assertEqual("500.00", result["amount_hnl"])
        with self.assertRaises(FinancialError):
            validate_source_payload({"channel": "Cash", "original_amount": "500", "exchange_rate": 1, "institution": "Banco"})

    def test_04_transfer_requires_reference(self) -> None:
        with self.assertRaisesRegex(FinancialError, "referencia"):
            validate_source_payload({"channel": "Transfer", "original_amount": "500", "exchange_rate": 1, "institution": "Banco", "account_reference": "123"})

    def test_05_multisource_outflow(self) -> None:
        ledger = AtomicLedger()
        ledger.create_source("R-A", 6000)
        ledger.create_source("R-B", 4000)
        result = ledger.execute(
            {"operation_type": "Outflow", "amount_hnl": 10000, "allocations": [{"source": "R-A", "amount_hnl": 6000}, {"source": "R-B", "amount_hnl": 4000}]},
            "outflow-1",
        )
        self.assertEqual("000000000001", result["document_number"])
        self.assertEqual(Decimal("0.00"), ledger.sources["R-A"].funds)
        self.assertEqual(Decimal("0.00"), ledger.sources["R-B"].funds)

    def test_06_reject_allocation_mismatch(self) -> None:
        with self.assertRaises(AllocationMismatch):
            preview_operation(
                {"operation_type": "Outflow", "amount_hnl": 10000, "allocations": [{"source": "R-A", "amount_hnl": 6000}]},
                {"R-A": SourceState.from_values(10000)},
            )

    def test_07_reject_overdraw(self) -> None:
        with self.assertRaises(InsufficientFunds):
            preview_operation(
                {"operation_type": "Outflow", "amount_hnl": 1001, "allocations": [{"source": "R-A", "amount_hnl": 1001}]},
                {"R-A": SourceState.from_values(1000)},
            )

    def test_08_concurrent_execution_serializes_source(self) -> None:
        ledger = AtomicLedger()
        ledger.create_source("R-A", 1000)
        start = threading.Barrier(2)

        def run(key: str) -> str:
            try:
                start.wait(timeout=2)
                ledger.execute(
                    {"operation_type": "Outflow", "amount_hnl": 700, "allocations": [{"source": "R-A", "amount_hnl": 700}]},
                    key,
                )
                return "ok"
            except InsufficientFunds:
                return "denied"

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = sorted(pool.map(run, ["c-1", "c-2"]))
        self.assertEqual(["denied", "ok"], results)
        self.assertEqual(Decimal("300.00"), ledger.sources["R-A"].funds)

    def test_09_same_key_same_payload_returns_same_result(self) -> None:
        ledger = AtomicLedger()
        ledger.create_source("R-A", 1000)
        payload = {"operation_type": "Outflow", "amount_hnl": 100, "allocations": [{"source": "R-A", "amount_hnl": 100}]}
        first = ledger.execute(payload, "same")
        second = ledger.execute(payload, "same")
        self.assertEqual(first, second)
        self.assertEqual(1, len(ledger.operations))

    def test_10_same_key_different_payload_is_rejected(self) -> None:
        ledger = AtomicLedger()
        ledger.create_source("R-A", 1000)
        ledger.execute({"operation_type": "Outflow", "amount_hnl": 100, "allocations": [{"source": "R-A", "amount_hnl": 100}]}, "same")
        with self.assertRaises(IdempotencyConflict):
            ledger.execute({"operation_type": "Outflow", "amount_hnl": 101, "allocations": [{"source": "R-A", "amount_hnl": 101}]}, "same")

    def test_11_failure_on_second_allocation_rolls_back_all_sources(self) -> None:
        ledger = AtomicLedger()
        ledger.create_source("R-A", 6000)
        ledger.create_source("R-B", 4000)
        with self.assertRaises(RuntimeError):
            ledger.execute(
                {"operation_type": "Outflow", "amount_hnl": 10000, "allocations": [{"source": "R-A", "amount_hnl": 6000}, {"source": "R-B", "amount_hnl": 4000}]},
                "rollback",
                fail_after_allocation=2,
            )
        self.assertEqual(Decimal("6000.00"), ledger.sources["R-A"].funds)
        self.assertEqual(Decimal("4000.00"), ledger.sources["R-B"].funds)
        self.assertNotIn("rollback", ledger.idempotency)
        result = ledger.execute(
            {"operation_type": "Outflow", "amount_hnl": 1, "allocations": [{"source": "R-A", "amount_hnl": 1}]},
            "after-gap",
        )
        self.assertEqual("000000000002", result["document_number"])

    def test_12_commitment_reserves_without_executing(self) -> None:
        ledger = AtomicLedger()
        ledger.create_source("R-A", 1000)
        ledger.execute({"operation_type": "Commitment Reserve", "amount_hnl": 400, "allocations": [{"source": "R-A", "amount_hnl": 400}]}, "reserve")
        self.assertEqual(SourceState.from_values(1000, 400), ledger.sources["R-A"])
        self.assertEqual(Decimal("600.00"), ledger.sources["R-A"].available)

    def test_13_commitment_execution_does_not_double_consume_available(self) -> None:
        ledger = AtomicLedger()
        ledger.create_source("R-A", 1000)
        ledger.execute({"operation_type": "Commitment Reserve", "amount_hnl": 400, "allocations": [{"source": "R-A", "amount_hnl": 400}]}, "reserve")
        available_before = ledger.sources["R-A"].available
        ledger.execute({"operation_type": "Commitment Execution", "amount_hnl": 400, "allocations": [{"source": "R-A", "amount_hnl": 400}]}, "execute")
        self.assertEqual(SourceState.from_values(600, 0), ledger.sources["R-A"])
        self.assertEqual(available_before, ledger.sources["R-A"].available)

    def test_14_release_commitment_restores_available(self) -> None:
        ledger = AtomicLedger()
        ledger.create_source("R-A", 1000)
        ledger.execute({"operation_type": "Commitment Reserve", "amount_hnl": 400, "allocations": [{"source": "R-A", "amount_hnl": 400}]}, "reserve")
        ledger.execute({"operation_type": "Commitment Release", "amount_hnl": 400, "allocations": [{"source": "R-A", "amount_hnl": 400}]}, "release")
        self.assertEqual(SourceState.from_values(1000, 0), ledger.sources["R-A"])

    def test_15_reclassification_does_not_restore_funds(self) -> None:
        ledger = AtomicLedger()
        ledger.create_source("R-A", 1000)
        ledger.execute({"operation_type": "Outflow", "amount_hnl": 200, "allocations": [{"source": "R-A", "amount_hnl": 200}]}, "out")
        ledger.execute({"operation_type": "Reclassification", "amount_hnl": 0, "allocations": [], "cost_center": "CC-2"}, "reclass")
        self.assertEqual(Decimal("800.00"), ledger.sources["R-A"].funds)

    def test_16_real_return_restores_only_proven_amount(self) -> None:
        ledger = AtomicLedger()
        ledger.create_source("R-A", 1000)
        ledger.execute({"operation_type": "Outflow", "amount_hnl": 400, "allocations": [{"source": "R-A", "amount_hnl": 400}]}, "out")
        with self.assertRaises(FinancialError):
            ledger.execute({"operation_type": "Real Return", "amount_hnl": 100, "allocations": [{"source": "R-A", "amount_hnl": 100}]}, "return-missing")
        ledger.execute({"operation_type": "Real Return", "amount_hnl": 100, "allocations": [{"source": "R-A", "amount_hnl": 100}], "evidence": "receipt.pdf"}, "return")
        self.assertEqual(Decimal("700.00"), ledger.sources["R-A"].funds)

    def test_17_all_document_numbers_have_twelve_digits(self) -> None:
        ledger = AtomicLedger()
        ledger.create_source("R-A", 10)
        for index in range(3):
            result = ledger.execute({"operation_type": "Outflow", "amount_hnl": 1, "allocations": [{"source": "R-A", "amount_hnl": 1}]}, f"n-{index}")
            self.assertRegex(result["document_number"], r"^\d{12}$")


if __name__ == "__main__":
    unittest.main()
