from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write
from nexora.financial.evidence_core import EVIDENCE_STATES, assert_evidence_transition, is_sha256
from nexora.financial.model_utils import validate_document_number

IMMUTABLE_CONTENT_FIELDS = (
	"document_number",
	"project",
	"evidence_kind",
	"channel",
	"file_url",
	"file_name",
	"mime_type",
	"file_size",
	"content_sha256",
	"source_message_date",
	"sender",
	"external_reference",
	"notes",
	"version",
	"supersedes",
	"uploaded_by",
	"uploaded_at",
	"idempotency_key",
	"payload_hash",
	"correlation_id",
)


class NXREvidence(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()

	def validate(self) -> None:
		validate_document_number(self.document_number)
		if self.status not in EVIDENCE_STATES:
			frappe.throw(_("Estado de evidencia desconocido."))
		if int(self.version or 0) < 1:
			frappe.throw(_("La versión de evidencia debe ser mayor o igual que uno."))
		if int(self.file_size or 0) <= 0:
			frappe.throw(_("La evidencia debe contener un archivo no vacío."))
		if not is_sha256(self.content_sha256):
			frappe.throw(_("La evidencia requiere una huella SHA-256 válida."))
		if self.is_new():
			if self.status != "Uploaded":
				frappe.throw(_("Una evidencia nueva debe iniciar en estado Cargada."))
			return

		previous = self.get_doc_before_save()
		if not previous:
			return
		changed = [
			fieldname
			for fieldname in IMMUTABLE_CONTENT_FIELDS
			if self.get(fieldname) != previous.get(fieldname)
		]
		if changed:
			frappe.throw(_("La evidencia es inmutable; campos alterados: {0}").format(", ".join(changed)))
		try:
			assert_evidence_transition(str(previous.status), str(self.status))
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		if self.status in {"Validated", "Rejected"} and (not self.reviewed_by or not self.reviewed_at):
			frappe.throw(_("La revisión de evidencia requiere revisor y fecha."))

	def on_trash(self) -> None:
		frappe.throw(_("Las evidencias NEXORA no se eliminan; deben conservarse o sustituirse."))
