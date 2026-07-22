from __future__ import annotations

import frappe
from frappe.model.document import Document

from nexora.financial.context import require_service_write
from nexora.financial.model_utils import money, rate, validate_document_number


class NXROperation(Document):
    def before_insert(self) -> None:
        require_service_write()

    def before_save(self) -> None:
        require_service_write()

    def validate(self) -> None:
        validate_document_number(self.document_number)
        amount = money(self.amount)
        exchange = rate(self.exchange_rate)
        if self.operation_type != "Reclassification" and amount <= 0:
            frappe.throw("El importe de la operación debe ser mayor que cero.")
        if exchange <= 0:
            frappe.throw("La tasa debe ser mayor que cero.")
        self.amount_hnl = money(amount * exchange)
        if self.operation_type in {"Outflow", "Real Return"}:
            identities = [self.requester, self.approved_by, self.executed_by]
            if any(not value for value in identities) or len(set(identities)) != 3:
                frappe.throw("Solicitante, aprobador y ejecutor deben ser tres usuarios distintos.")
        if self.operation_type == "Real Return" and not self.evidence:
            frappe.throw("Una devolución real requiere evidencia.")
