from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SETUP = ROOT / "erpnext" / "construcontrol" / "expense_setup.py"
RULES = ROOT / "erpnext" / "construcontrol" / "expenses.py"
FORM = ROOT / "erpnext" / "public" / "js" / "construcontrol_expenses.js"
HOOKS = ROOT / "erpnext" / "hooks.py"


class ExpenseContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.setup = SETUP.read_text(encoding="utf-8")
        cls.rules = RULES.read_text(encoding="utf-8")
        cls.form = FORM.read_text(encoding="utf-8")
        cls.hooks = HOOKS.read_text(encoding="utf-8")

    def test_professional_invoice_and_payment_fields_exist(self) -> None:
        for fieldname in (
            "invoice_number",
            "due_date",
            "subtotal_hnl",
            "tax_hnl",
            "withholding_hnl",
            "discount_hnl",
            "paid_amount_hnl",
            "balance_due_hnl",
            "professional_approval_status",
            "payment_evidence",
        ):
            self.assertIn(fieldname, self.setup)

    def test_standard_fields_are_reused_instead_of_duplicated(self) -> None:
        self.assertIn("_exclude_standard_fields", self.setup)
        self.assertIn('"DocField"', self.setup)
        self.assertIn("reusing standard fields", self.setup)
        self.assertIn("create_custom_fields(_exclude_standard_fields(definitions), update=True)", self.setup)

    def test_server_enforces_totals_duplicates_and_approval(self) -> None:
        self.assertIn("subtotal + tax - withholding - discount", self.rules)
        self.assertIn("_validate_duplicate_invoice", self.rules)
        self.assertIn("El monto pagado no puede superar", self.rules)
        self.assertIn("Indique el motivo del rechazo", self.rules)
        self.assertIn("Ingrese la referencia del pago", self.rules)

    def test_payable_is_synchronized_without_deleting_history(self) -> None:
        self.assertIn("sync_payable_from_expense", self.rules)
        self.assertIn("archive_payable_from_expense", self.rules)
        self.assertIn("is_logically_deleted", self.rules)
        self.assertNotIn("delete_doc", self.rules)

    def test_form_exposes_approval_and_payment_workflow(self) -> None:
        for label in ("Enviar a aprobación", "Aprobar", "Rechazar", "Ver cuentas por pagar"):
            self.assertIn(label, self.form)
        self.assertIn("validate_professional_expense", self.hooks)
        self.assertIn("sync_payable_from_expense", self.hooks)


if __name__ == "__main__":
    unittest.main()
