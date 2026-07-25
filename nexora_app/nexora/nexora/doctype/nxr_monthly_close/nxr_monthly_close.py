from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write


class NXRMonthlyClose(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()

	def validate(self) -> None:
		if self.total_inflows_hnl is not None and self.total_outflows_hnl is not None:
			self.net_flow_hnl = self.total_inflows_hnl - self.total_outflows_hnl

	def on_trash(self) -> None:
		frappe.throw(_("Los cierres mensuales NEXORA no se eliminan."))
