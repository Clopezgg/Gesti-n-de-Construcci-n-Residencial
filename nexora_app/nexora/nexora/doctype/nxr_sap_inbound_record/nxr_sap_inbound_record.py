from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write


class NXRSAPInboundRecord(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()

	def on_trash(self) -> None:
		frappe.throw(
			_(
				"Los registros entrantes de SAP no se eliminan — son la bitácora real de qué se trajo y "
				"cuándo, igual que un evento de auditoría."
			)
		)
