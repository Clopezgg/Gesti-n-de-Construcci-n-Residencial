from frappe.model.document import Document

from nexora.contracts.core import validate_period


class NXRContractEvidence(Document):
	def validate(self) -> None:
		validate_period(self.valid_from, self.valid_until)
