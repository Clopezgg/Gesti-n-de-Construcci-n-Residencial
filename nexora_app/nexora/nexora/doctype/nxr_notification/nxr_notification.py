from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write


class NXRNotification(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()

	def validate(self) -> None:
		pass

	def on_trash(self) -> None:
		frappe.throw(_("Las notificaciones NEXORA no se eliminan."))
