from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write
from nexora.financial.model_utils import validate_document_number
from nexora.purchases.quotation_core import QUOTATION_TRANSITIONS


def _line_total(rows: list[dict[str, Any]]) -> str:
	total = 0.0
	for row in rows:
		qty = float(row.get("quantity") or 0)
		rate = float(row.get("unit_rate") or 0)
		total += qty * rate
	return f"{total:.2f}"


class NXRSupplierQuotation(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()

	def validate(self) -> None:
		validate_document_number(self.document_number)
		if self.status not in QUOTATION_TRANSITIONS:
			frappe.throw(_("Estado de cotización desconocido."))
		if not self.valid_until:
			frappe.throw(_("La cotización requiere fecha de vencimiento."))
		if not self.lines:
			frappe.throw(_("La cotización requiere al menos una línea."))
		self.total_amount = _line_total([row.as_dict() for row in self.lines])
		if float(self.total_amount or 0) <= 0:
			frappe.throw(_("El total cotizado debe ser mayor que cero."))

	def before_submit(self) -> None:
		require_service_write()

	def on_trash(self) -> None:
		frappe.throw(_("Las cotizaciones no se eliminan."))
