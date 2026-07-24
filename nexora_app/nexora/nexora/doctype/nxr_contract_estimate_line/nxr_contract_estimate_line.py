
import frappe
from frappe import _
from frappe.model.document import Document
from nexora.contracts.core import money

class NXRContractEstimateLine(Document):
    def validate(self) -> None:
        if money(self.quantity) <= 0 or money(self.amount) <= 0:
            frappe.throw(_("La línea estimada requiere cantidad e importe positivos."))
