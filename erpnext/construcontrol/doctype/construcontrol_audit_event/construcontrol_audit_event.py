from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class ConstruControlAuditEvent(Document):
	def validate(self) -> None:
		if not self.is_new():
			frappe.throw(_("ConstruControl audit events are append-only."))

	def on_trash(self) -> None:
		frappe.throw(_("ConstruControl audit events cannot be deleted."))
