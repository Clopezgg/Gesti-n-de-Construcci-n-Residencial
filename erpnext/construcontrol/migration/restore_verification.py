from __future__ import annotations

import frappe


def count_records(doctype: str) -> dict[str, object]:
	"""Return an internal, zero-safe record count for isolated restore verification."""
	normalized = str(doctype or "").strip()
	if not normalized or not frappe.db.exists("DocType", normalized):
		raise frappe.ValidationError(f"Unknown DocType for restore verification: {normalized or '<empty>'}")
	return {
		"doctype": normalized,
		"count": int(frappe.db.count(normalized)),
	}
