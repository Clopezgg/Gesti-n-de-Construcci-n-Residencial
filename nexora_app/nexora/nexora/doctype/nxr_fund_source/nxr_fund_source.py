from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write
from nexora.financial.model_utils import money, rate

BANK_CHANNELS = {"Deposit", "Transfer"}
RECONCILIATION_FIELDS = (
	"reconciliation_status",
	"reconciled_by",
	"reconciled_at",
	"reconciliation_method",
	"reconciliation_difference_hnl",
	"reconciliation_note",
	"reconciliation_evidence",
)
IMMUTABLE_SOURCE_FIELDS = (
	"source_code",
	"channel",
	"source_date",
	"currency",
	"original_amount",
	"exchange_rate",
	"amount_hnl",
	"origin_or_sender",
	"custodian",
	"remittance",
)
GUIDED_CORRECTION_FIELDS = {
	"channel",
	"source_date",
	"currency",
	"original_amount",
	"exchange_rate",
	"amount_hnl",
	"origin_or_sender",
}


class NXRFundSource(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_validate(self) -> None:
		if self.is_new() or not self.request_cancellation:
			return
		previous = self.get_doc_before_save()
		if not previous or previous.status == "Cancelled":
			self.request_cancellation = 0
			return
		from nexora.financial.sources import cancel_fund_source_document

		cancel_fund_source_document(self, self.cancellation_reason)
		self.flags.nexora_cancelled_by_service = True

	def validate(self) -> None:
		original = money(self.original_amount)
		exchange = rate(self.exchange_rate)
		if original <= 0 or exchange <= 0:
			frappe.throw(_("El importe y la tasa deben ser mayores que cero."))
		self.amount_hnl = money(original * exchange)
		previous = None if self.is_new() else self.get_doc_before_save()
		if previous:
			changed = [
				fieldname
				for fieldname in IMMUTABLE_SOURCE_FIELDS
				if self.get(fieldname) != previous.get(fieldname)
			]
			if changed:
				allowed = GUIDED_CORRECTION_FIELDS if self.flags.nexora_documentary_correction else set()
				blocked = [fieldname for fieldname in changed if fieldname not in allowed]
				if blocked:
					frappe.throw(_("Documento inmutable; campos alterados: {0}").format(", ".join(blocked)))
		if previous and any(
			getattr(self, field, None) != getattr(previous, field, None) for field in RECONCILIATION_FIELDS
		):
			require_service_write()
		if previous and self.status != previous.status:
			is_safe_cancellation = bool(
				self.flags.nexora_cancelled_by_service
				and previous.status in {"Active", "Exhausted"}
				and self.status == "Cancelled"
			)
			if not is_safe_cancellation:
				require_service_write()
		if self.reconciliation_status not in {"Pending", "Reconciled", "Disputed"}:
			frappe.throw(_("El estado de conciliación no es válido."))
		if self.reconciliation_status == "Pending":
			if self.reconciled_by or self.reconciled_at:
				frappe.throw(_("Una conciliación pendiente no puede conservar responsable ni fecha."))
		elif not self.reconciled_by or not self.reconciled_at or not self.reconciliation_method:
			frappe.throw(_("La conciliación requiere responsable, fecha y método."))
		if self.reconciliation_status == "Disputed" and (
			not self.reconciliation_note or not self.reconciliation_evidence
		):
			frappe.throw(_("Una conciliación en disputa requiere observación y evidencia."))
		if self.status == "Cancelled":
			if not self.cancellation_reason or len(self.cancellation_reason.strip()) < 10:
				frappe.throw(_("Una anulación requiere un motivo de al menos 10 caracteres."))
			if not self.cancellation_operation or not self.cancelled_by or not self.cancelled_at:
				frappe.throw(_("La anulación debe conservar su operación, responsable y fecha."))
		if self.channel == "Cash":
			if self.institution or self.account_reference:
				frappe.throw(_("El efectivo no debe exigir ni almacenar institución o cuenta bancaria."))
		elif self.channel in BANK_CHANNELS:
			missing = [
				label
				for label, value in (
					("institución", self.institution),
					("cuenta", self.account_reference),
					("referencia", self.external_reference),
				)
				if not value
			]
			if missing:
				frappe.throw(_("{0} requiere {1}.").format(self.channel, ", ".join(missing)))
