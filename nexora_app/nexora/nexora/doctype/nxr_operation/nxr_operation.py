from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write
from nexora.financial.model_utils import money, rate, validate_document_number
from nexora.financial.reference_rules import SEGREGATED_OPERATION_CODES, validate_advance_dates


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
		if self.operation_code in SEGREGATED_OPERATION_CODES:
			identities = [self.requester, self.approved_by, self.executed_by]
			if any(not value for value in identities) or len(set(identities)) != 3:
				frappe.throw(_("Solicitante, aprobador y ejecutor deben ser tres usuarios distintos."))
		if self.operation_code == "ADVANCE_DISBURSEMENT":
			if not self.beneficiary:
				frappe.throw(_("El anticipo requiere beneficiario o responsable."))
			try:
				validate_advance_dates(self.operation_date, self.due_date)
			except ValueError as exc:
				frappe.throw(_(str(exc)))
		if self.operation_type == "Real Return" and not self.evidence:
			frappe.throw(_("Una devolución real requiere evidencia."))
