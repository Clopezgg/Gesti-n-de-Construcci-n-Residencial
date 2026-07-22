from __future__ import annotations

from frappe.model.document import Document

from nexora.financial.context import require_service_write
from nexora.financial.model_utils import validate_document_number, validate_immutable


class NXRDocumentSequence(Document):
    def before_insert(self) -> None:
        require_service_write()
        validate_document_number(self.number)

    def validate(self) -> None:
        validate_document_number(self.number)
        validate_immutable(self, ("number", "issued_for_doctype", "idempotency_key"))
