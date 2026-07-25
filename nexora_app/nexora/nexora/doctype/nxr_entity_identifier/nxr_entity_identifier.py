from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write


class NXREntityIdentifier(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()

	def validate(self) -> None:
		if not self.identifier_type:
			frappe.throw(_("El identificador requiere tipo."))
		if not self.identifier_value:
			frappe.throw(_("El identificador requiere valor protegido."))
		if not self.masked_value:
			frappe.throw(_("El identificador requiere representación enmascarada."))
		digest = str(self.normalized_hash or "")
		if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest.lower()):
			frappe.throw(_("El identificador requiere una huella normalizada SHA-256."))
