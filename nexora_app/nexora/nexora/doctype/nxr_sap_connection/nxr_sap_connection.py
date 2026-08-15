from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write


class NXRSAPConnection(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()

	def on_trash(self) -> None:
		frappe.throw(_("Las conexiones SAP no se eliminan; desactive la conexión o guarde un valor nuevo."))
