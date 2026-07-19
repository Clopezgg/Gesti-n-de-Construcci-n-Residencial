from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FINANCE = ROOT / "erpnext" / "construcontrol" / "finance.py"
SETUP = ROOT / "erpnext" / "construcontrol" / "finance_setup.py"
DEFINITION = ROOT / "erpnext" / "construcontrol" / "runtime" / "definitions_06.json"
FORM = ROOT / "erpnext" / "public" / "js" / "construcontrol_finance.js"
INSTALL = ROOT / "erpnext" / "construcontrol" / "install.py"


class FinanceContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.finance = FINANCE.read_text(encoding="utf-8")
        cls.setup = SETUP.read_text(encoding="utf-8")
        cls.form = FORM.read_text(encoding="utf-8")
        cls.install = INSTALL.read_text(encoding="utf-8")
        cls.definition = json.loads(DEFINITION.read_text(encoding="utf-8"))[0]

    def test_institution_catalog_is_administrable_and_protected(self) -> None:
        self.assertEqual(self.definition["name"], "CC Financial Institution")
        fieldnames = {field["fieldname"] for field in self.definition["fields"]}
        self.assertTrue({"logo_file", "brand_color", "is_active", "is_protected"}.issubset(fieldnames))
        self.assertIn("protect_financial_institution_delete", self.finance)
        self.assertIn("Puede desactivarla, pero no eliminarla", self.finance)

    def test_professional_treasury_fields_are_installed(self) -> None:
        for fieldname in (
            "transaction_channel",
            "financial_institution",
            "gross_amount",
            "fee_amount",
            "net_amount",
            "treasury_exchange_rate",
            "net_amount_hnl",
            "reconciliation_status",
            "treasury_evidence",
        ):
            self.assertIn(fieldname, self.setup)
        self.assertIn("ensure_finance_configuration()", self.install)

    def test_amounts_and_reconciliation_are_validated_server_side(self) -> None:
        self.assertIn("net = gross - fee", self.finance)
        self.assertIn("net_hnl = net * rate", self.finance)
        self.assertIn("La comisión no puede superar", self.finance)
        self.assertIn("Una operación conciliada debe tener fecha", self.finance)

    def test_form_displays_uploaded_logo_or_safe_fallback(self) -> None:
        self.assertIn("logo_file || visual.logo_path", self.form)
        self.assertIn("cc-institution-badge", self.form)
        self.assertIn("fallbackBadge", self.form)


if __name__ == "__main__":
    unittest.main()
