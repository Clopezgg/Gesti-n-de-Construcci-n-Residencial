from __future__ import annotations

from unittest import TestCase

from nexora.purchases.receipt_core import (
	GOODS_RECEIPT_TRANSITIONS,
	PurchaseValidationError,
	assert_receipt_transition,
	compute_po_completion_status,
	validate_receipt_lines,
)


class TestGoodsReceiptCore(TestCase):
	def test_draft_can_be_completed(self) -> None:
		try:
			assert_receipt_transition("Draft", "Completed")
		except PurchaseValidationError:
			self.fail("Draft -> Completed debería ser válido")

	def test_draft_can_be_cancelled(self) -> None:
		try:
			assert_receipt_transition("Draft", "Cancelled")
		except PurchaseValidationError:
			self.fail("Draft -> Cancelled debería ser válido")

	def test_completed_is_terminal(self) -> None:
		with self.assertRaises(PurchaseValidationError):
			assert_receipt_transition("Completed", "Draft")

	def test_cancelled_is_terminal(self) -> None:
		with self.assertRaises(PurchaseValidationError):
			assert_receipt_transition("Cancelled", "Draft")

	def test_all_transitions_are_defined(self) -> None:
		for state, targets in GOODS_RECEIPT_TRANSITIONS.items():
			for target in targets:
				try:
					assert_receipt_transition(state, target)
				except PurchaseValidationError:
					self.fail(f"{state} -> {target} debería ser válido")

	def test_unknown_source_is_rejected(self) -> None:
		with self.assertRaises(PurchaseValidationError):
			assert_receipt_transition("Unknown", "Draft")

	def test_validate_receipt_lines_within_tolerance(self) -> None:
		order_lines = [{"name": "L001", "quantity": "100", "line_code": "001"}]
		lines = [{"purchase_order_line": "L001", "quantity": "105", "rejected_quantity": "0"}]
		result = validate_receipt_lines(lines, order_lines)
		self.assertIn("L001", result)
		# `quantity()` cuantiza a seis decimales (mismo invariante que verifica
		# `test_inventory_core.py::test_quantity_rounds_to_six_decimals`), no
		# dos como el dinero — no una decisión de este archivo.
		self.assertEqual("105.000000", str(result["L001"]))

	def test_validate_receipt_lines_exceeds_tolerance(self) -> None:
		order_lines = [{"name": "L001", "quantity": "100", "line_code": "001"}]
		lines = [{"purchase_order_line": "L001", "quantity": "120", "rejected_quantity": "0"}]
		with self.assertRaises(PurchaseValidationError):
			validate_receipt_lines(lines, order_lines)

	def test_negative_quantity_rejected(self) -> None:
		order_lines = [{"name": "L001", "quantity": "100", "line_code": "001"}]
		with self.assertRaises(PurchaseValidationError):
			validate_receipt_lines(
				[{"purchase_order_line": "L001", "quantity": "-5", "rejected_quantity": "0"}], order_lines
			)

	def test_negative_rejected_rejected(self) -> None:
		order_lines = [{"name": "L001", "quantity": "100", "line_code": "001"}]
		with self.assertRaises(PurchaseValidationError):
			validate_receipt_lines(
				[{"purchase_order_line": "L001", "quantity": "10", "rejected_quantity": "-1"}], order_lines
			)

	def test_no_purchase_order_line_ref_rejected(self) -> None:
		with self.assertRaises(PurchaseValidationError):
			validate_receipt_lines(
				[{"purchase_order_line": "", "quantity": "10", "rejected_quantity": "0"}], []
			)

	# NXR-COM-0010: dos recepciones parciales de la misma línea deben acumularse contra
	# la tolerancia, no evaluarse cada una de forma aislada.

	def test_validate_receipt_lines_accumulates_previous_receipts_within_tolerance(self) -> None:
		order_lines = [{"name": "L001", "quantity": "100", "line_code": "001"}]
		lines = [
			{
				"purchase_order_line": "L001",
				"quantity": "50",
				"rejected_quantity": "0",
				"previously_received": "50",
			}
		]
		result = validate_receipt_lines(lines, order_lines)
		self.assertEqual("50.000000", str(result["L001"]))

	def test_validate_receipt_lines_rejects_cumulative_over_receipt(self) -> None:
		# Ordenado 100, tolerancia por defecto 10% (máximo 110). Ya se recibieron 90 en
		# una recepción previa; esta segunda recepción de 30 es, por sí sola, menor que
		# el máximo (110), pero acumulada (90 + 30 = 120) excede la tolerancia. Antes de
		# esta corrección esto se aceptaba sin error.
		order_lines = [{"name": "L001", "quantity": "100", "line_code": "001"}]
		lines = [
			{
				"purchase_order_line": "L001",
				"quantity": "30",
				"rejected_quantity": "0",
				"previously_received": "90",
			}
		]
		with self.assertRaises(PurchaseValidationError):
			validate_receipt_lines(lines, order_lines)

	def test_validate_receipt_lines_without_previously_received_defaults_to_zero(self) -> None:
		order_lines = [{"name": "L001", "quantity": "100", "line_code": "001"}]
		lines = [{"purchase_order_line": "L001", "quantity": "105", "rejected_quantity": "0"}]
		result = validate_receipt_lines(lines, order_lines)
		self.assertEqual("105.000000", str(result["L001"]))


class TestPurchaseOrderCompletionStatus(TestCase):
	def test_completed_when_every_line_fully_received(self) -> None:
		order_lines = [
			{"name": "L001", "quantity": "100"},
			{"name": "L002", "quantity": "20"},
		]
		totals = {"L001": "100", "L002": "20"}
		self.assertEqual("Completed", compute_po_completion_status(order_lines, totals))

	def test_completed_when_a_line_is_received_above_ordered_quantity(self) -> None:
		order_lines = [{"name": "L001", "quantity": "100"}]
		totals = {"L001": "105"}
		self.assertEqual("Completed", compute_po_completion_status(order_lines, totals))

	def test_sent_when_any_line_is_only_partially_received(self) -> None:
		order_lines = [
			{"name": "L001", "quantity": "100"},
			{"name": "L002", "quantity": "20"},
		]
		totals = {"L001": "100", "L002": "5"}
		self.assertEqual("Sent", compute_po_completion_status(order_lines, totals))

	def test_sent_when_a_line_has_no_receipts_yet(self) -> None:
		order_lines = [{"name": "L001", "quantity": "100"}]
		self.assertEqual("Sent", compute_po_completion_status(order_lines, {}))
