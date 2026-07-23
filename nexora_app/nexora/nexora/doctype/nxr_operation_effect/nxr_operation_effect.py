from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write
from nexora.financial.model_utils import money, validate_immutable


class NXROperationEffect(Document):
	def before_insert(self) -> None:
		require_service_write()

	def validate(self) -> None:
		if money(self.amount_hnl) == 0:
			frappe.throw(_("Un efecto canónico no puede ser cero."))
		validate_immutable(
			self,
			(
				"operation",
				"fund_source",
				"commitment",
				"dimension",
				"effect_type",
				"amount_hnl",
				"correlation_id",
			),
		)
