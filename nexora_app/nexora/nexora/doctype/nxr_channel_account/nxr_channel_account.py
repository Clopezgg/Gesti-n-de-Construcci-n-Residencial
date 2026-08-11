from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write


class NXRChannelAccount(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()

	def validate(self) -> None:
		if self.status != "Active":
			return
		duplicate = frappe.db.exists(
			"NXR Channel Account",
			{
				"channel": self.channel,
				"external_id": self.external_id,
				"status": "Active",
				"name": ["!=", self.name],
			},
		)
		if duplicate:
			frappe.throw(
				_("Ya existe una cuenta activa de este canal vinculada a esa identidad externa.")
			)
