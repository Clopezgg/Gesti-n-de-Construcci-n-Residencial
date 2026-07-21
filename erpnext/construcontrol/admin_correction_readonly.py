from __future__ import annotations

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

_DERIVED_EXPENSE_FIELDS = (
	"status",
	"financial_status",
	"calculated_total_hnl",
	"approved_amount_hnl",
	"balance_due_hnl",
)


def ensure_derived_expense_fields_are_read_only() -> None:
	"""Prevent normal forms from presenting calculated financial state as editable."""
	if not frappe.db.exists("DocType", "CC Expense Control"):
		return
	meta = frappe.get_meta("CC Expense Control")
	for fieldname in _DERIVED_EXPENSE_FIELDS:
		field = meta.get_field(fieldname)
		if not field:
			continue
		make_property_setter(
			"CC Expense Control",
			fieldname,
			"read_only",
			"1",
			"Check",
			validate_fields_for_doctype=False,
		)
	frappe.clear_cache(doctype="CC Expense Control")
	print("[ConstruControl] derived expense fields are read-only", flush=True)


__all__ = ["ensure_derived_expense_fields_are_read_only"]
