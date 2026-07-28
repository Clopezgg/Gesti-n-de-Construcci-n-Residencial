from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write
from nexora.financial.model_utils import money


class NXROperationEffect(Document):
	def before_insert(self) -> None:
		require_service_write()

	def validate(self) -> None:
		if money(self.amount_hnl) == 0:
			frappe.throw(_("Un efecto canónico no puede ser cero."))
		if self.is_new():
			return
		previous = self.get_doc_before_save()
		if not previous:
			return
		immutable_fields = (
			"operation",
			"fund_source",
			"commitment",
			"dimension",
			"effect_type",
			"amount_hnl",
			"correlation_id",
		)
		changed = [
			fieldname for fieldname in immutable_fields if self.get(fieldname) != previous.get(fieldname)
		]
		if not changed:
			return
		allowed = {"amount_hnl"} if self.flags.nexora_documentary_correction else set()
		blocked = [fieldname for fieldname in changed if fieldname not in allowed]
		if blocked:
			frappe.throw(_("Documento inmutable; campos alterados: {0}").format(", ".join(blocked)))
