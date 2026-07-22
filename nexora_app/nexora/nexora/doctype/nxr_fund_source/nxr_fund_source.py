from __future__ import annotations

import frappe
from frappe.model.document import Document

from nexora.financial.context import require_service_write
from nexora.financial.model_utils import money, rate, validate_immutable

BANK_CHANNELS = {"Deposit", "Transfer"}


class NXRFundSource(Document):
    def before_insert(self) -> None:
        require_service_write()

    def validate(self) -> None:
        original = money(self.original_amount)
        exchange = rate(self.exchange_rate)
        if original <= 0 or exchange <= 0:
            frappe.throw("El importe y la tasa deben ser mayores que cero.")
        self.amount_hnl = money(original * exchange)
        validate_immutable(
            self,
            (
                "source_code",
                "channel",
                "project",
                "source_date",
                "currency",
                "original_amount",
                "exchange_rate",
                "amount_hnl",
                "origin_or_sender",
                "custodian",
            ),
        )
        previous = None if self.is_new() else self.get_doc_before_save()
        if previous and self.status != previous.status:
            require_service_write()
        if self.channel == "Cash":
            if self.institution or self.account_reference:
                frappe.throw("El efectivo no debe exigir ni almacenar institución o cuenta bancaria.")
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
                frappe.throw(f"{self.channel} requiere {', '.join(missing)}.")
