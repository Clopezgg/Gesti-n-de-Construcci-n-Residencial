from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write

BANK_CHANNELS = {"Deposit", "Transfer", "Remittance"}


class NXRFinancialAccount(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		if not self.is_new():
			require_service_write()

	def validate(self) -> None:
		if self.direction not in {"Origin", "Destination", "Both"}:
			frappe.throw(_("El uso de la cuenta financiera no es válido."))
		if self.default_channel not in {"Remittance", "Cash", "Deposit", "Transfer", "Other"}:
			frappe.throw(_("El canal habitual no es válido."))
		if not str(self.account_name or "").strip() or not str(self.origin_or_sender or "").strip():
			frappe.throw(_("La cuenta frecuente requiere nombre y titular o remitente."))
		if self.default_channel == "Cash":
			if self.institution or self.account_reference:
				frappe.throw(_("Una cuenta frecuente de efectivo no debe almacenar banco ni número de cuenta."))
		elif self.default_channel in BANK_CHANNELS and (
			not str(self.institution or "").strip() or not str(self.account_reference or "").strip()
		):
			frappe.throw(_("La cuenta frecuente requiere banco o remesadora y número de cuenta."))
