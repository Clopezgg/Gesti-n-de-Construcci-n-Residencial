from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write
from nexora.financial.model_utils import money, validate_document_number


class NXRCommitment(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()

	def validate(self) -> None:
		validate_document_number(self.document_number)
		if money(self.amount_hnl) <= 0:
			frappe.throw(_("El compromiso debe ser mayor que cero."))
		if self.requester and self.approved_by and self.requester == self.approved_by:
			frappe.throw(_("El solicitante no puede autoaprobar el compromiso."))
