from __future__ import annotations

import json
import pathlib
import unittest

APP = pathlib.Path(__file__).resolve().parents[2]
DOCTYPE_ROOT = APP / "nexora/nexora/doctype"

EXPECTED = {
    "nxr_document_sequence": "NXR Document Sequence",
    "nxr_fund_source": "NXR Fund Source",
    "nxr_operation": "NXR Operation",
    "nxr_operation_effect": "NXR Operation Effect",
    "nxr_fund_allocation": "NXR Fund Allocation",
    "nxr_commitment": "NXR Commitment",
    "nxr_idempotency_record": "NXR Idempotency Record",
    "nxr_audit_event": "NXR Audit Event",
}


class TestFinancialModelContract(unittest.TestCase):
    def test_all_canonical_doctypes_exist(self) -> None:
        for slug, name in EXPECTED.items():
            payload = json.loads((DOCTYPE_ROOT / slug / f"{slug}.json").read_text(encoding="utf-8"))
            self.assertEqual(name, payload["name"])
            self.assertEqual("NEXORA", payload["module"])

    def test_document_sequence_is_unique_and_read_only(self) -> None:
        payload = json.loads(
            (DOCTYPE_ROOT / "nxr_document_sequence/nxr_document_sequence.json").read_text(encoding="utf-8")
        )
        number = next(field for field in payload["fields"] if field["fieldname"] == "number")
        self.assertEqual(1, number["unique"])
        self.assertEqual(1, number["read_only"])

    def test_no_legacy_inventory_ledger_is_written(self) -> None:
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in APP.rglob("*.py")
            if "/tests/" not in path.as_posix()
        )
        self.assertNotIn('new_doc("CC Material Ledger")', text)
        self.assertNotIn('get_doc({"doctype": "CC Material Ledger"', text)

    def test_mariadb_counter_is_native_auto_increment(self) -> None:
        patch = (APP / "nexora/patches/v0_1/create_sequence_counter.py").read_text(encoding="utf-8")
        self.assertIn("AUTO_INCREMENT", patch)
        self.assertIn("ENGINE=InnoDB", patch)


if __name__ == "__main__":
    unittest.main()
