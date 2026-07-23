from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write
from nexora.financial.model_utils import money, validate_immutable


class NXRFundAllocation(Document):
	def before_insert(self) -> None:
		require_service_write()

	def validate(self) -> None:
		if money(self.allocated_amount_hnl) <= 0:
			frappe.throw(_("La asignación debe ser mayor que cero."))
		validate_immutable(
			self,
			(
				"operation",
				"fund_source",
				"related_source",
				"commitment",
				"allocated_amount_hnl",
				"balance_before_hnl",
				"balance_after_hnl",
				"reserved_before_hnl",
				"reserved_after_hnl",
				"allocation_order",
				"correlation_id",
			),
		)
