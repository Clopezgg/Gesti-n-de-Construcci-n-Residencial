from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.contracts.core import (
	ESTIMATE_TRANSITIONS,
	assert_transition,
	estimate_amounts,
	money,
	validate_period,
)
from nexora.financial.context import require_service_write
from nexora.financial.model_utils import validate_document_number


class NXRContractEstimate(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()

	def validate(self) -> None:
		validate_document_number(self.document_number)
		if self.status not in ESTIMATE_TRANSITIONS:
			frappe.throw(_("Estado de estimación desconocido."))
		try:
			validate_period(self.period_start, self.period_end)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		gross = money(sum((money(row.amount) for row in self.lines), money(0)))
		values = estimate_amounts(
			gross, self.advance_amortization, self.retention_amount, self.fine_amount, self.deduction_amount
		)
		self.gross_amount = values.gross
		self.payable_amount = values.payable
		if any(row.cost_kind != self.cost_kind for row in self.lines):
			frappe.throw(_("Una estimación no puede mezclar materiales y mano de obra."))
		if self.is_new():
			return
		previous = self.get_doc_before_save()
		if not previous:
			return
		try:
			assert_transition(str(previous.status), str(self.status), ESTIMATE_TRANSITIONS)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		if previous.status in {"Paid", "Rejected", "Cancelled"}:
			fields = (
				"status",
				"contract",
				"estimate_sequence",
				"period_start",
				"period_end",
				"cost_kind",
				"gross_amount",
				"advance_amortization",
				"retention_amount",
				"fine_amount",
				"deduction_amount",
				"payable_amount",
				"evidence",
				"operation",
				"advance_operation",
				"paid_at",
			)
			if any(self.get(field) != previous.get(field) for field in fields):
				frappe.throw(_("La estimación terminal es inmutable."))

	def on_trash(self) -> None:
		frappe.throw(_("Las estimaciones no se eliminan."))
