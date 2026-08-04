from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write
from nexora.financial.model_utils import money, rate, validate_document_number
from nexora.financial.reference_rules import SEGREGATED_OPERATION_CODES, validate_advance_dates

OPERATION_TRANSITIONS = {
	"Draft": {"Validated", "Cancelled"},
	"Validated": {"Pending Approval", "Cancelled"},
	"Pending Approval": {"Approved", "Rejected", "Cancelled"},
	"Approved": {"Executed", "Cancelled"},
	"Executed": {"Compensated Partial", "Compensated Total"},
	"Compensated Partial": {"Compensated Total"},
	"Cancelled": set(),
	"Rejected": set(),
	"Compensated Total": set(),
}
EXECUTED_STATUSES = {"Executed", "Compensated Partial", "Compensated Total"}
IMMUTABLE_EXECUTED_FIELDS = (
	"document_number",
	"operation_code",
	"operation_type",
	"project",
	"target_project",
	"destination_source",
	"operation_date",
	"due_date",
	"currency",
	"amount",
	"exchange_rate",
	"amount_hnl",
	"beneficiary_doctype",
	"beneficiary",
	"cost_center",
	"economic_category",
	"payment_method",
	"external_reference",
	"affects_cost",
	"affects_budget",
	"commitment",
	"idempotency_key",
	"payload_hash",
	"preview_hash",
	"requester",
	"approved_by",
	"executed_by",
	"evidence",
	"reference_doctype",
	"reference_name",
	"reference_amount_hnl",
	"reference_balance_before_hnl",
	"reference_balance_after_hnl",
	"reversal_of",
	"substitutes_operation",
	"correlation_id",
)
GUIDED_CORRECTION_FIELDS = {
	"operation_date",
	"amount",
	"exchange_rate",
	"amount_hnl",
	"external_reference",
	"evidence",
}


class NXROperation(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()

	def validate(self) -> None:
		validate_document_number(self.document_number)
		amount = money(self.amount)
		exchange = rate(self.exchange_rate)
		if self.operation_code == "DOCUMENT_SUBSTITUTION":
			if amount != 0:
				frappe.throw(_("Una sustitución documental debe tener importe cero."))
		elif amount <= 0:
			frappe.throw(_("El importe de la operación debe ser mayor que cero."))
		if exchange <= 0:
			frappe.throw(_("La tasa debe ser mayor que cero."))
		self.amount_hnl = money(amount * exchange)
		guided_correction = bool(
			self.flags.nexora_guided_correction and self.operation_code == "DOCUMENT_SUBSTITUTION"
		)
		if self.operation_code in SEGREGATED_OPERATION_CODES and not guided_correction:
			identities = [self.requester, self.approved_by, self.executed_by]
			# executed_by es de solo lectura y lo fija el servicio al ejecutar, así que
			# faltar un actor y repetirlo son fallos distintos y se explican distinto.
			if any(not value for value in identities):
				frappe.throw(
					_(
						"Indique solicitante y aprobador. Junto con el ejecutor, que es quien "
						"registra la operación, deben ser tres usuarios distintos."
					)
				)
			if len(set(identities)) != 3:
				frappe.throw(
					_(
						"Solicitante, aprobador y ejecutor deben ser tres usuarios distintos. "
						"El ejecutor es quien registra la operación, así que elija un solicitante "
						"y un aprobador distintos de él y entre sí."
					)
				)
		if self.operation_code == "ADVANCE_DISBURSEMENT":
			if not self.beneficiary:
				frappe.throw(_("El anticipo requiere beneficiario o responsable."))
			try:
				validate_advance_dates(self.operation_date, self.due_date)
			except ValueError as exc:
				frappe.throw(_(str(exc)))
		if self.operation_type == "Real Return" and not self.evidence:
			frappe.throw(_("Una devolución real requiere evidencia."))
		self._validate_state_and_immutability()

	def _validate_state_and_immutability(self) -> None:
		if self.status not in OPERATION_TRANSITIONS:
			frappe.throw(_("Estado de operación desconocido."))
		if self.is_new():
			return
		previous = self.get_doc_before_save()
		if not previous:
			return
		if previous.status != self.status and self.status not in OPERATION_TRANSITIONS.get(
			previous.status, set()
		):
			frappe.throw(
				_("Transición de operación no permitida: {0} → {1}.").format(previous.status, self.status)
			)
		if previous.status in EXECUTED_STATUSES:
			changed = [
				fieldname
				for fieldname in IMMUTABLE_EXECUTED_FIELDS
				if self.get(fieldname) != previous.get(fieldname)
			]
			if changed:
				allowed = GUIDED_CORRECTION_FIELDS if self.flags.nexora_documentary_correction else set()
				blocked = [fieldname for fieldname in changed if fieldname not in allowed]
				if blocked:
					frappe.throw(
						_("La operación ejecutada es inmutable; campos alterados: {0}").format(
							", ".join(blocked)
						)
					)

	def on_trash(self) -> None:
		if self.status in EXECUTED_STATUSES:
			frappe.throw(_("Una operación ejecutada no puede eliminarse; use un documento compensatorio."))
