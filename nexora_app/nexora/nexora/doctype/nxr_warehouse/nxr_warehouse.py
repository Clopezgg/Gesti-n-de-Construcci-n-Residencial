from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class NXRWarehouse(Document):
	def before_insert(self) -> None:
		from nexora.financial.context import require_service_write

		require_service_write()

	def before_save(self) -> None:
		from nexora.financial.context import require_service_write

		require_service_write()

	def on_trash(self) -> None:
		frappe.throw(_("Las bodegas no se eliminan."))
