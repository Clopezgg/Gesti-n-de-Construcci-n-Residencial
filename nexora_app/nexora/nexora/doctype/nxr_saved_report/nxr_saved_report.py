from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write


class NXRSavedReport(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()

	def validate(self) -> None:
		if not str(self.document_number or "").isdigit() or len(str(self.document_number)) != 12:
			frappe.throw(_("El reporte guardado requiere un número numérico único de 12 dígitos."))
		if self.report_code not in {"BI01", "FI01", "FI02", "FI03", "CO01", "PR02", "PR03", "MM03"}:
			frappe.throw(_("El tipo de reporte guardado no es válido."))

	def on_trash(self) -> None:
		frappe.throw(_("Los reportes guardados NEXORA no se eliminan; deben archivarse."))
