from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class NXREconomicCategory(Document):
	def validate(self) -> None:
		for fieldname in ("cost_factor", "budget_factor", "savings_factor", "investment_factor"):
			if hasattr(self, fieldname) and int(self.get(fieldname) or 0) not in {-1, 0, 1}:
				frappe.throw(_("Los factores analíticos solo pueden ser -1, 0 o 1."))
		if not self.is_new():
			previous = self.get_doc_before_save()
			if previous and self.code != previous.code:
				frappe.throw(_("El código de catálogo es inmutable."))

	def on_trash(self) -> None:
		if self.system_managed:
			frappe.throw(_("Un catálogo oficial no puede eliminarse; desactívelo."))
