from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class NXROperationType(Document):
	def validate(self) -> None:
		if not self.is_new():
			previous = self.get_doc_before_save()
			if previous and self.code != previous.code:
				frappe.throw(_("El código de catálogo es inmutable."))
			if previous and previous.system_managed and self.kernel_type != previous.kernel_type:
				frappe.throw(_("El tipo canónico administrado por el sistema es inmutable."))

	def on_trash(self) -> None:
		if self.system_managed:
			frappe.throw(_("Un catálogo oficial no puede eliminarse; desactívelo."))
