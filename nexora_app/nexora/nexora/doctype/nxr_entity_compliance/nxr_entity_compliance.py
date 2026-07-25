from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.directory.core import (
	COMPLIANCE_STATES,
	COMPLIANCE_TRANSITIONS,
	assert_transition,
	validate_period,
)
from nexora.financial.context import require_service_write
from nexora.financial.model_utils import validate_document_number

IMMUTABLE_COMPLIANCE_FIELDS = (
	"document_number",
	"entity",
	"compliance_type",
	"valid_from",
	"valid_until",
	"created_by_user",
	"created_at",
	"idempotency_key",
	"payload_hash",
	"correlation_id",
)


class NXREntityCompliance(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()

	def validate(self) -> None:
		validate_document_number(self.document_number)
		if self.status not in COMPLIANCE_STATES:
			frappe.throw(_("Estado de cumplimiento desconocido."))
		if not frappe.db.exists("NXR Entity", self.entity):
			frappe.throw(_("La entidad del cumplimiento no existe."))
		try:
			validate_period(self.valid_from, self.valid_until)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		if self.status in {"Current", "Approved Exception"} and not self.evidence:
			frappe.throw(_("El cumplimiento vigente o exceptuado requiere evidencia."))
		if self.is_new():
			if self.status != "Pending":
				frappe.throw(_("Un control de cumplimiento nuevo debe iniciar en estado Pending."))
			return
		previous = self.get_doc_before_save()
		if not previous:
			return
		try:
			assert_transition(str(previous.status), str(self.status), COMPLIANCE_TRANSITIONS)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		changed = [
			fieldname
			for fieldname in IMMUTABLE_COMPLIANCE_FIELDS
			if self.get(fieldname) != previous.get(fieldname)
		]
		if changed:
			frappe.throw(_("El alcance del cumplimiento es inmutable; cree un control nuevo."))
		if self.evidence != previous.evidence:
			allowed_attachment = (
				not previous.evidence
				and bool(self.evidence)
				and previous.status in {"Pending", "Expired"}
				and self.status in {"Current", "Approved Exception"}
			)
			if not allowed_attachment:
				frappe.throw(_("La evidencia de cumplimiento no puede sustituirse silenciosamente."))
		if self.status != previous.status and (not self.reviewed_by or not self.reviewed_at):
			frappe.throw(_("La transición de cumplimiento requiere actor y fecha de revisión."))

	def on_trash(self) -> None:
		frappe.throw(_("Los controles de cumplimiento no se eliminan; conservan su historial."))
