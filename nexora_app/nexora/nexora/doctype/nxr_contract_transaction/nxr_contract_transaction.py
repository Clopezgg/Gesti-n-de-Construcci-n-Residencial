from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.contracts.core import money
from nexora.financial.context import require_service_write
from nexora.financial.model_utils import validate_document_number


class NXRContractTransaction(Document):
    def before_insert(self) -> None:
        require_service_write()

    def before_save(self) -> None:
        require_service_write()

    def validate(self) -> None:
        validate_document_number(self.document_number)
        if money(self.amount) < 0:
            frappe.throw(_("El movimiento contractual no admite importe negativo."))
        if self.is_new():
            return
        previous = self.get_doc_before_save()
        fields = (
            "contract", "estimate", "transaction_type", "transaction_date", "currency", "amount",
            "operation", "reference_transaction", "correction_operation", "evidence", "notes", "idempotency_key", "payload_hash", "correlation_id",
        )
        if previous and any(self.get(field) != previous.get(field) for field in fields):
            frappe.throw(_("El movimiento contractual es inmutable."))
        if previous and self.status != previous.status and not (previous.status == "Executed" and self.status == "Reversed"):
            frappe.throw(_("Transición de movimiento contractual no permitida."))

    def on_trash(self) -> None:
        frappe.throw(_("Los movimientos contractuales no se eliminan."))
