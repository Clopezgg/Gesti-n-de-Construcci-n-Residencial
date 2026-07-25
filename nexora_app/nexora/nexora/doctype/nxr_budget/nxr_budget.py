from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write
from nexora.financial.model_utils import money, validate_document_number


class NXRBudget(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()

	def validate(self) -> None:
		validate_document_number(self.document_number)
		if self.total_approved_hnl is not None and money(self.total_approved_hnl) < 0:
			frappe.throw(_("El total aprobado no puede ser negativo."))
		if not self.lines:
			frappe.throw(_("El presupuesto debe tener al menos una línea."))

	def on_trash(self) -> None:
		frappe.throw(_("Los presupuestos NEXORA no se eliminan."))
