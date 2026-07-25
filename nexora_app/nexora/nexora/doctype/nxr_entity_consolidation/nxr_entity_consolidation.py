from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write
from nexora.financial.model_utils import validate_document_number

IMMUTABLE_FIELDS = (
	"document_number",
	"source_entity",
	"target_entity",
	"reason",
	"source_snapshot_hash",
	"consolidated_by",
	"consolidated_at",
	"idempotency_key",
	"payload_hash",
	"correlation_id",
)


class NXREntityConsolidation(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()

	def validate(self) -> None:
		validate_document_number(self.document_number)
		if not self.source_entity or not self.target_entity or self.source_entity == self.target_entity:
			frappe.throw(_("La consolidación requiere origen y destino diferentes."))
		if not frappe.db.exists("NXR Entity", self.source_entity) or not frappe.db.exists(
			"NXR Entity", self.target_entity
		):
			frappe.throw(_("La consolidación contiene una entidad inexistente."))
		if len(str(self.source_snapshot_hash or "")) != 64:
			frappe.throw(_("La consolidación requiere huella del expediente de origen."))
		if self.is_new():
			return
		previous = self.get_doc_before_save()
		if previous and any(self.get(fieldname) != previous.get(fieldname) for fieldname in IMMUTABLE_FIELDS):
			frappe.throw(_("El expediente de consolidación es inmutable."))

	def on_trash(self) -> None:
		frappe.throw(_("Los expedientes de consolidación no se eliminan."))
