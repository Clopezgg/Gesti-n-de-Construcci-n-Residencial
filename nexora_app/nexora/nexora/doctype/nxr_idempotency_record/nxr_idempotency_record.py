from __future__ import annotations

from frappe.model.document import Document

from nexora.financial.context import require_service_write
from nexora.financial.model_utils import validate_immutable


class NXRIdempotencyRecord(Document):
    def before_insert(self) -> None:
        require_service_write()

    def before_save(self) -> None:
        require_service_write()

    def validate(self) -> None:
        validate_immutable(self, ("idempotency_key", "payload_hash", "correlation_id"))
