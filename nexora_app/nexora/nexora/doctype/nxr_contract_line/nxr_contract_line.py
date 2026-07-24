
from frappe.model.document import Document
from nexora.contracts.core import money

class NXRContractLine(Document):
    def validate(self) -> None:
        self.amount = money(self.quantity) * money(self.unit_rate)
        if not self.current_amount:
            self.current_amount = self.amount
