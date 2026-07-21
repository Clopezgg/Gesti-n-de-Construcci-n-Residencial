from __future__ import annotations

import re
from typing import Any

import frappe
from frappe import _

from erpnext.construcontrol.access import require_construcontrol_access

_DEMO_PATTERN = re.compile(
	r"(?:^|\b)(demo|sample|example|test|dummy|fictitious|ejemplo|prueba|muestra)(?:\b|$)",
	re.IGNORECASE,
)

_TARGETS: tuple[tuple[str, tuple[str, ...]], ...] = (
	("Company", ("name", "company_name", "abbr")),
	("Customer", ("name", "customer_name")),
	("Supplier", ("name", "supplier_name")),
	("Item", ("name", "item_code", "item_name")),
	("Project", ("name", "project_name")),
	("Warehouse", ("name", "warehouse_name")),
	("Cost Center", ("name", "cost_center_name")),
)


def classify_demo_label(*values: Any) -> tuple[bool, str]:
	normalized = " ".join(str(value or "").strip() for value in values if value is not None).strip()
	if not normalized:
		return False, "empty"
	if _DEMO_PATTERN.search(normalized):
		return True, "name-pattern"
	return False, "not-demo"


def _dependency_count(doctype: str, name: str) -> int:
	count = 0
	links = frappe.get_all(
		"DocField",
		filters={"fieldtype": "Link", "options": doctype},
		fields=["parent", "fieldname"],
		limit_page_length=0,
	)
	custom_links = frappe.get_all(
		"Custom Field",
		filters={"fieldtype": "Link", "options": doctype},
		fields=["dt as parent", "fieldname"],
		limit_page_length=0,
	)
	for link in [*links, *custom_links]:
		parent = str(link.get("parent") or "")
		fieldname = str(link.get("fieldname") or "")
		if not parent or not fieldname or not frappe.db.exists("DocType", parent):
			continue
		try:
			count += int(frappe.db.count(parent, filters={fieldname: name}))
		except Exception:
			continue
	return count


@frappe.whitelist()
def inventory_demo_data() -> dict[str, Any]:
	require_construcontrol_access()
	if "System Manager" not in set(frappe.get_roles()):
		frappe.throw(
			_("Solo System Manager puede inventariar datos demo."),
			frappe.PermissionError,
		)

	candidates: list[dict[str, Any]] = []
	reviewed = 0
	for doctype, fields in _TARGETS:
		available = [
			field for field in fields if frappe.get_meta(doctype).has_field(field) or field == "name"
		]
		rows = frappe.get_all(doctype, fields=available, limit_page_length=0)
		reviewed += len(rows)
		for row in rows:
			values = [row.get(field) for field in available]
			is_demo, reason = classify_demo_label(*values)
			if not is_demo:
				continue
			name = str(row.get("name") or "")
			candidates.append(
				{
					"doctype": doctype,
					"name": name,
					"reason": reason,
					"dependencies": _dependency_count(doctype, name),
					"classification": "candidate-demo",
					"action": "review-required",
				}
			)

	candidates.sort(key=lambda row: (row["doctype"], row["name"]))
	return {
		"status": "inventory-only",
		"reviewed_records": reviewed,
		"candidate_count": len(candidates),
		"candidates": candidates,
		"destructive_action_performed": False,
		"warning": "No se eliminó ningún registro. Cada candidato requiere revisión y respaldo.",
	}
