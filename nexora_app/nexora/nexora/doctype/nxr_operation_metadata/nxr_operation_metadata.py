from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write

MOVEMENT_CODES = {"101", "102", "303", "304", "501"}


class NXROperationMetadata(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		if not self.is_new():
			require_service_write()

	def validate(self) -> None:
		if str(self.movement_code or "") not in MOVEMENT_CODES:
			frappe.throw(_("El código operativo no es válido."))
		if not frappe.db.exists("NXR Operation", self.operation):
			frappe.throw(_("La operación asociada no existe."))
