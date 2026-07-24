from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.contracts.core import (
	CONTRACT_TRANSITIONS,
	assert_transition,
	line_amounts,
	money,
	validate_period,
)
from nexora.financial.context import require_service_write
from nexora.financial.model_utils import validate_document_number

IMMUTABLE_AFTER_ACTIVE = (
	"document_number",
	"contractor",
	"contractor_profile",
	"modality",
	"project",
	"cost_center",
	"fund_source",
	"responsible",
	"scope",
	"currency",
	"exchange_rate",
	"original_labor_amount",
	"original_material_amount",
	"original_amount",
	"start_date",
	"original_end_date",
	"idempotency_key",
	"payload_hash",
	"correlation_id",
)
TERMINAL = {"Liquidated", "Early Terminated", "Cancelled Before Active"}


class NXRContract(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()

	def validate(self) -> None:
		validate_document_number(self.document_number)
		if self.status not in CONTRACT_TRANSITIONS:
			frappe.throw(_("Estado contractual desconocido."))
		try:
			validate_period(self.start_date, self.original_end_date)
			validate_period(self.start_date, self.current_end_date)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		amounts = line_amounts([row.as_dict() for row in self.lines])
		if (
			money(self.original_labor_amount) != amounts.labor
			or money(self.original_material_amount) != amounts.materials
		):
			frappe.throw(_("Los importes originales deben coincidir con las líneas contractuales."))
		if money(self.original_amount) != amounts.total:
			frappe.throw(_("El monto original contractual no concilia."))
		if money(self.current_amount) != money(self.current_labor_amount) + money(
			self.current_material_amount
		):
			frappe.throw(_("El monto vigente contractual no concilia."))
		executed = money(self.executed_labor_amount) + money(self.executed_material_amount)
		pending = money(self.current_amount) - executed
		if pending < 0:
			frappe.throw(_("La ejecución contractual no puede superar el monto vigente."))
		self.executed_amount = money(executed)
		self.pending_amount = money(pending)
		if money(self.advance_balance) != money(self.advance_disbursed) - money(self.advance_amortized):
			frappe.throw(_("El saldo anticipado no concilia."))
		if money(self.retention_balance) != money(self.retention_held) - money(self.retention_returned):
			frappe.throw(_("El saldo retenido no concilia."))
		if self.is_new():
			return
		previous = self.get_doc_before_save()
		if not previous:
			return
		try:
			assert_transition(str(previous.status), str(self.status), CONTRACT_TRANSITIONS)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		if previous.status in {"Active", "Suspended", "Completed", "In Liquidation", *TERMINAL}:
			changed = [field for field in IMMUTABLE_AFTER_ACTIVE if self.get(field) != previous.get(field)]
			if changed:
				frappe.throw(
					_("El contrato ejecutado es inmutable; use una adenda: {0}").format(", ".join(changed))
				)
		if previous.status in TERMINAL:
			terminal_fields = (
				"status",
				"current_scope",
				"current_labor_amount",
				"current_material_amount",
				"current_amount",
				"current_end_date",
				"version",
				"executed_labor_amount",
				"executed_material_amount",
				"executed_amount",
				"pending_amount",
				"paid_amount",
				"advance_disbursed",
				"advance_amortized",
				"advance_balance",
				"retention_held",
				"retention_returned",
				"retention_balance",
				"fine_amount",
				"deduction_amount",
				"suspension_reason",
			)
			if any(self.get(field) != previous.get(field) for field in terminal_fields):
				frappe.throw(_("El contrato terminal es inmutable."))

	def on_trash(self) -> None:
		frappe.throw(_("Los contratos NEXORA no se eliminan."))
