from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.model_utils import money


class NXRRemittanceDestination(Document):
	def validate(self) -> None:
		if money(self.amount_hnl) <= 0:
			frappe.throw(_("El importe de cada destino debe ser mayor que cero."))
