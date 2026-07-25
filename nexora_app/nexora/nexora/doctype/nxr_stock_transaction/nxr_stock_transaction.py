from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write
from nexora.financial.model_utils import validate_document_number


class NXRStockTransaction(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()

	def validate(self) -> None:
		validate_document_number(self.document_number)
		if not self.lines:
			frappe.throw(_("El movimiento requiere al menos una línea."))

	def on_trash(self) -> None:
		frappe.throw(_("Los movimientos de inventario no se eliminan."))
