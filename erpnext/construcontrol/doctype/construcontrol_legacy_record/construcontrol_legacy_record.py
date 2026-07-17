from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class ConstruControlLegacyRecord(Document):
	def validate(self) -> None:
		if self.is_new():
			return
		before = self.get_doc_before_save()
		if before and (before.raw_payload != self.raw_payload or before.payload_hash != self.payload_hash):
			frappe.throw(_("Legacy payloads are immutable; import a new version instead."))

	def on_trash(self) -> None:
		if "System Manager" not in frappe.get_roles() and "ConstruControl Manager" not in frappe.get_roles():
			frappe.throw(_("Only migration managers may remove legacy records."))
