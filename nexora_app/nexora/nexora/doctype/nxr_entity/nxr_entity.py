from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.directory.core import (
	ENTITY_STATES,
	ENTITY_TRANSITIONS,
	assert_transition,
	normalize_name,
	unique_nonempty,
	validate_period,
)
from nexora.financial.context import require_service_write
from nexora.financial.model_utils import validate_document_number

TERMINAL_ENTITY_FIELDS = (
	"document_number",
	"status",
	"entity_type",
	"display_name",
	"normalized_name",
	"legal_name",
	"linked_user",
	"country",
	"date_of_birth",
	"merged_into",
	"consolidation_record",
	"notes",
	"idempotency_key",
	"payload_hash",
	"correlation_id",
)


class NXREntity(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()

	def validate(self) -> None:
		validate_document_number(self.document_number)
		if self.status not in ENTITY_STATES:
			frappe.throw(_("Estado de entidad desconocido."))
		if not str(self.display_name or "").strip():
			frappe.throw(_("La entidad requiere nombre visible."))
		self.normalized_name = normalize_name(self.display_name)
		if not self.normalized_name:
			frappe.throw(_("El nombre de entidad no produce una forma normalizada válida."))
		if self.linked_user:
			if self.linked_user == "Guest" or not frappe.db.exists("User", self.linked_user):
				frappe.throw(_("El usuario vinculado no existe o no puede ser Guest."))
		identifier_hashes = [row.normalized_hash for row in self.identifiers]
		contact_hashes = [row.normalized_hash for row in self.contacts]
		if not unique_nonempty(identifier_hashes):
			frappe.throw(_("La entidad contiene identificadores duplicados."))
		if not unique_nonempty(contact_hashes):
			frappe.throw(_("La entidad contiene contactos duplicados."))
		for row in [*self.identifiers, *self.contacts]:
			try:
				validate_period(row.valid_from, row.valid_until)
			except ValueError as exc:
				frappe.throw(_(str(exc)))
		if self.status == "Active" and not (self.identifiers or self.contacts or self.linked_user):
			frappe.throw(_("Una entidad activa requiere identificador, contacto o usuario vinculado."))
		if self.status == "Consolidated" and (not self.merged_into or not self.consolidation_record):
			frappe.throw(_("Una entidad consolidada requiere destino y expediente de consolidación."))
		self._validate_transition_and_terminal_immutability()

	def _validate_transition_and_terminal_immutability(self) -> None:
		if self.is_new():
			if self.status != "Draft":
				frappe.throw(_("Una entidad nueva debe iniciar en estado Draft."))
			return
		previous = self.get_doc_before_save()
		if not previous:
			return
		try:
			assert_transition(str(previous.status), str(self.status), ENTITY_TRANSITIONS)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		if previous.status in {"Inactive", "Consolidated"}:
			changed = [
				fieldname
				for fieldname in TERMINAL_ENTITY_FIELDS
				if self.get(fieldname) != previous.get(fieldname)
			]
			if changed or self.identifiers != previous.identifiers or self.contacts != previous.contacts:
				frappe.throw(_("La entidad terminal es inmutable y conserva su expediente original."))

	def on_trash(self) -> None:
		frappe.throw(_("Las entidades NEXORA no se eliminan; deben inactivarse o consolidarse."))
