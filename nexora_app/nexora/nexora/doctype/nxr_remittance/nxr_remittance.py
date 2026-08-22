from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.central_treasury import CENTRAL_REMITTANCE_KEY
from nexora.financial.context import require_service_write
from nexora.financial.model_utils import money, rate, validate_immutable

IMMUTABLE_REMITTANCE_FIELDS = (
	"remittance_code",
	"financial_account",
	"project",
	"remittance_date",
	"currency",
	"total_original_amount",
	"exchange_rate",
	"total_amount_hnl",
	"origin_or_sender",
	"custodian",
)


class NXRRemittance(Document):
	def before_insert(self) -> None:
		require_service_write()

	def validate(self) -> None:
		if self.is_new() and not self.financial_account:
			frappe.throw(_("La remesa requiere la Cuenta Central de Remesas."))
		if self.financial_account:
			technical_key = frappe.db.get_value(
				"NXR Financial Account", self.financial_account, "technical_key"
			)
			if technical_key != CENTRAL_REMITTANCE_KEY:
				frappe.throw(_("La remesa solo puede registrarse en la Cuenta Central de Remesas."))
		original = money(self.total_original_amount)
		exchange = rate(self.exchange_rate)
		if original <= 0 or exchange <= 0:
			frappe.throw(_("El importe total y la tasa deben ser mayores que cero."))
		self.total_amount_hnl = money(original * exchange)
		if not self.destinations:
			frappe.throw(_("Una remesa requiere al menos un destino."))
		allocated = money(sum(money(row.amount_hnl) for row in self.destinations))
		if allocated != self.total_amount_hnl:
			frappe.throw(
				_("Los destinos suman {0} y la remesa exige {1}.").format(
					f"{allocated:.2f}", f"{self.total_amount_hnl:.2f}"
				)
			)
		validate_immutable(self, IMMUTABLE_REMITTANCE_FIELDS)
		previous = None if self.is_new() else self.get_doc_before_save()
		if previous and self.status != previous.status:
			require_service_write()
		if self.status == "Cancelled":
			if not self.cancellation_reason or len(self.cancellation_reason.strip()) < 10:
				frappe.throw(_("Una anulación requiere un motivo de al menos 10 caracteres."))
			if not self.cancelled_by or not self.cancelled_at:
				frappe.throw(_("La anulación debe conservar responsable y fecha."))

	def on_trash(self) -> None:
		frappe.throw(_("Una remesa no puede eliminarse; use la cancelación."))
