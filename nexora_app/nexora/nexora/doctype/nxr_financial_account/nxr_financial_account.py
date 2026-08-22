from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write

BANK_CHANNELS = {"Deposit", "Transfer", "Remittance"}
SYSTEM_MANAGED_FIELDS = (
	"account_name",
	"account_role",
	"technical_key",
	"system_managed",
	"active",
	"project",
	"direction",
	"origin_or_sender",
	"institution",
	"account_reference",
	"currency",
	"default_channel",
	"is_default",
	"account_fingerprint",
)


class NXRFinancialAccount(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		if not self.is_new():
			require_service_write()

	def validate(self) -> None:
		if self.account_role not in {"Counterparty", "Treasury"}:
			frappe.throw(_("El rol de la cuenta financiera no es válido."))
		if self.direction not in {"Origin", "Destination", "Both"}:
			frappe.throw(_("El uso de la cuenta financiera no es válido."))
		if self.default_channel not in {"Remittance", "Cash", "Deposit", "Transfer", "Other"}:
			frappe.throw(_("El canal habitual no es válido."))
		if not str(self.account_name or "").strip() or not str(self.origin_or_sender or "").strip():
			frappe.throw(_("La cuenta frecuente requiere nombre y titular o remitente."))
		if self.system_managed and not str(self.technical_key or "").strip():
			frappe.throw(_("Una cuenta administrada por el sistema requiere clave técnica."))
		if self.technical_key and not self.system_managed:
			frappe.throw(_("Una cuenta con clave técnica debe estar administrada por el sistema."))
		if self.account_role == "Treasury":
			if not self.system_managed or self.project:
				frappe.throw(_("La cuenta de tesorería debe ser global y administrada por el sistema."))
			if self.currency != "HNL" or self.default_channel != "Remittance":
				frappe.throw(_("La Cuenta Central de Remesas opera en HNL y canal Remittance."))
			if self.institution or self.account_reference:
				frappe.throw(_("La cuenta lógica de tesorería no almacena datos bancarios inventados."))
		elif self.default_channel == "Cash":
			if self.institution or self.account_reference:
				frappe.throw(
					_("Una cuenta frecuente de efectivo no debe almacenar banco ni número de cuenta.")
				)
		elif self.default_channel in BANK_CHANNELS and (
			not str(self.institution or "").strip() or not str(self.account_reference or "").strip()
		):
			frappe.throw(_("La cuenta frecuente requiere banco o remesadora y número de cuenta."))
		if self.is_new():
			return
		previous = self.get_doc_before_save()
		if previous and previous.system_managed:
			changed = [field for field in SYSTEM_MANAGED_FIELDS if self.get(field) != previous.get(field)]
			if changed:
				frappe.throw(
					_("La cuenta administrada por el sistema es inmutable: {0}").format(", ".join(changed))
				)

	def on_trash(self) -> None:
		frappe.throw(_("Las cuentas financieras NEXORA no se eliminan; desactive las cuentas ordinarias."))
