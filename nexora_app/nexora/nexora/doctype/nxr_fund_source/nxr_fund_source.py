from __future__ import annotations

import frappe
from frappe.model.document import Document

from nexora.financial.model_utils import money, rate

BANK_CHANNELS = {"Deposit", "Transfer"}


class NXRFundSource(Document):
    def validate(self) -> None:
        original = money(self.original_amount)
        exchange = rate(self.exchange_rate)
        if original <= 0 or exchange <= 0:
            frappe.throw("El importe y la tasa deben ser mayores que cero.")
        self.amount_hnl = money(original * exchange)
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
