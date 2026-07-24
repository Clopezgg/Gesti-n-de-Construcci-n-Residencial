from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.directory.core import validate_period
from nexora.financial.context import require_service_write
from nexora.financial.model_utils import validate_document_number
from nexora.purchases.core import (
	SUPPLIER_PROFILE_TRANSITIONS,
	assert_transition,
	normalize_classification,
)


class NXRSupplierProfile(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()

	def validate(self) -> None:
		validate_document_number(self.document_number)
		try:
			validate_period(self.valid_from, self.valid_until)
			self.classification = normalize_classification(self.classification)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		if self.status not in SUPPLIER_PROFILE_TRANSITIONS:
			frappe.throw(_("Estado de proveedor desconocido."))
		if self.is_new():
			return
		previous = self.get_doc_before_save()
		if not previous:
			return
		try:
			assert_transition(str(previous.status), str(self.status), SUPPLIER_PROFILE_TRANSITIONS)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		if previous.status == "Inactive":
			fields = (
				"status",
				"entity",
				"entity_role",
				"classification",
				"valid_from",
				"valid_until",
				"compliance",
				"compliance_status",
				"evidence",
				"notes",
			)
			if any(self.get(field) != previous.get(field) for field in fields):
				frappe.throw(_("El perfil de proveedor inactivo es inmutable."))

	def on_trash(self) -> None:
		frappe.throw(_("Los perfiles de proveedor no se eliminan."))
