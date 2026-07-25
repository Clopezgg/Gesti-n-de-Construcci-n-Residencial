from __future__ import annotations

ENTITY_TYPES = frozenset({"Individual", "Organization"})
IDENTIFIER_TYPES = frozenset({"National Id", "Rtn", "Passport", "Tax Id", "Email", "Internal Code", "Other"})
CONTACT_TYPES = frozenset({"Email", "Phone", "Mobile", "Whatsapp", "Address", "Other"})
ROLE_TYPES = frozenset(
	{
		"Administrator",
		"Contractor",
		"Supplier",
		"Employee",
		"Beneficiary",
		"Customer",
		"Contact",
		"Donor",
		"Owner",
		"Other",
	}
)
COMPLIANCE_TYPES = frozenset(
	{"Identity", "Tax", "Contractual", "Banking", "Supplier", "Labor", "Insurance", "Other"}
)
