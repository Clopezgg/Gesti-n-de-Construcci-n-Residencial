from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.contracts.core import PROFILE_TRANSITIONS, assert_transition, validate_period
from nexora.financial.context import require_service_write
from nexora.financial.model_utils import validate_document_number


class NXRContractorProfile(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()

	def validate(self) -> None:
		validate_document_number(self.document_number)
		try:
			validate_period(self.valid_from, self.valid_until)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		if self.status not in PROFILE_TRANSITIONS:
			frappe.throw(_("Estado de contratista desconocido."))
		if self.is_new():
			return
		previous = self.get_doc_before_save()
		if not previous:
			return
		try:
			assert_transition(str(previous.status), str(self.status), PROFILE_TRANSITIONS)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		if previous.status == "Inactive":
			fields = (
				"status",
				"entity",
				"classification",
				"valid_from",
				"valid_until",
				"compliance_status",
				"evidence",
				"notes",
			)
			if any(self.get(field) != previous.get(field) for field in fields):
				frappe.throw(_("El perfil inactivo es inmutable."))

	def on_trash(self) -> None:
		frappe.throw(_("Los perfiles de contratista no se eliminan."))
