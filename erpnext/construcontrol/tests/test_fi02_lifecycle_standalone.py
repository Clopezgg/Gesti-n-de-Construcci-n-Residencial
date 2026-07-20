from __future__ import annotations

import ast
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "expenses.py"


class FI02LifecycleContractTest(unittest.TestCase):
	@classmethod
	def setUpClass(cls) -> None:
		cls.source = MODULE.read_text(encoding="utf-8")
		cls.tree = ast.parse(cls.source)
		cls.functions = {
			node.name
			for node in cls.tree.body
			if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
		}

	def test_server_validation_owns_the_complete_fi02_lifecycle(self) -> None:
		self.assertTrue(
			{
				"validate_professional_expense",
				"sync_payable_from_expense",
				"archive_payable_from_expense",
				"backfill_professional_expenses",
			}.issubset(self.functions)
		)

	def test_total_uses_explicit_zero_and_rejects_invalid_amounts(self) -> None:
		self.assertIn('raw_subtotal not in (None, "")', self.source)
		self.assertIn("El total del gasto debe ser mayor que cero", self.source)
		self.assertIn("no pueden superar el subtotal más impuestos", self.source)

	def test_approval_and_payment_changes_require_manager_authority(self) -> None:
		self.assertIn("aprobar, rechazar o reabrir gastos", self.source)
		self.assertIn("registrar pagos, anulaciones o reembolsos", self.source)
		self.assertIn("validation_bypass_active()", self.source)

	def test_partial_and_full_payments_require_traceable_evidence(self) -> None:
		for requirement in (
			"Ingrese la referencia del pago",
			"Ingrese la fecha del pago",
			"Adjunte el comprobante del pago",
		):
			self.assertIn(requirement, self.source)
		self.assertIn("_validate_duplicate_payment_reference", self.source)

	def test_approved_financial_content_is_frozen(self) -> None:
		self.assertIn("_PROTECTED_APPROVED_FIELDS", self.source)
		self.assertIn("Devuelva el gasto a pendiente", self.source)
		self.assertIn("ya tiene pagos", self.source)

	def test_duplicate_invoices_and_payables_are_blocked(self) -> None:
		self.assertIn("_validate_duplicate_invoice", self.source)
		self.assertIn("cuentas por pagar duplicadas", self.source)
		self.assertIn("by_source and by_expense and by_source != by_expense", self.source)

	def test_only_approved_active_expenses_generate_payables(self) -> None:
		self.assertIn('approved = _approval_state(doc) == "approved"', self.source)
		self.assertIn("or not approved", self.source)
		self.assertIn("_archive_payable(existing)", self.source)

	def test_standard_and_professional_approval_fields_stay_synchronized(self) -> None:
		self.assertIn("_set_approval_fields(doc, approval_status)", self.source)
		self.assertIn('"approval_status": _APPROVAL_FIELD_MAP.get', self.source)


if __name__ == "__main__":
	unittest.main()
