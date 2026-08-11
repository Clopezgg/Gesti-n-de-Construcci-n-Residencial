from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.conversation.core import ConversationValidationError, assert_pending_intent_transition
from nexora.financial.context import require_service_write


class NXRConversationPendingIntent(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()

	def validate(self) -> None:
		if self.is_new():
			return
		previous = self.get_doc_before_save()
		if not previous:
			return
		try:
			assert_pending_intent_transition(str(previous.status), str(self.status))
		except ConversationValidationError as exc:
			frappe.throw(_(str(exc)))
