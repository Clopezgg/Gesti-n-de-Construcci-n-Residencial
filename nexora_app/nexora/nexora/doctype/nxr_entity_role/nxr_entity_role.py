from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.directory.core import ROLE_STATES, ROLE_TRANSITIONS, assert_transition, validate_period
from nexora.financial.context import require_service_write
from nexora.financial.model_utils import validate_document_number

IMMUTABLE_ROLE_FIELDS = (
	"document_number",
	"entity",
	"role_type",
	"project",
	"valid_from",
	"valid_until",
	"assigned_by",
	"assigned_at",
	"idempotency_key",
	"payload_hash",
	"correlation_id",
)


class NXREntityRole(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()

	def validate(self) -> None:
		validate_document_number(self.document_number)
		if self.status not in ROLE_STATES:
			frappe.throw(_("Estado de rol de entidad desconocido."))
		if not frappe.db.exists("NXR Entity", self.entity):
			frappe.throw(_("La entidad del rol no existe."))
		try:
			validate_period(self.valid_from, self.valid_until)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		if self.is_new():
			if self.status != "Proposed":
				frappe.throw(_("Un rol nuevo debe iniciar en estado Proposed."))
			return
		previous = self.get_doc_before_save()
		if not previous:
			return
		try:
			assert_transition(str(previous.status), str(self.status), ROLE_TRANSITIONS)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		changed = [
			fieldname for fieldname in IMMUTABLE_ROLE_FIELDS if self.get(fieldname) != previous.get(fieldname)
		]
		if changed:
			frappe.throw(_("El alcance y la vigencia del rol son inmutables; cree una asignación nueva."))
		if self.status != previous.status and (not self.reviewed_by or not self.reviewed_at):
			frappe.throw(_("La transición del rol requiere actor y fecha de revisión."))

	def on_trash(self) -> None:
		frappe.throw(_("Las asignaciones de rol no se eliminan; deben expirar o revocarse."))
