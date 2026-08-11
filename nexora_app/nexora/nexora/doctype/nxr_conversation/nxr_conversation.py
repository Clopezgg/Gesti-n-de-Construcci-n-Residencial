from __future__ import annotations

from frappe.model.document import Document

from nexora.financial.context import require_service_write


class NXRConversation(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()
