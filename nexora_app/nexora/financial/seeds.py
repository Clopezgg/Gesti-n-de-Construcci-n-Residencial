from __future__ import annotations

import frappe

from nexora.financial.catalog import category_rows, operation_rows


def _upsert(doctype: str, code: str, values: dict[str, object]) -> None:
	if frappe.db.exists(doctype, code):
		frappe.db.set_value(doctype, code, values, update_modified=False)
	else:
		frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)


def seed_analytic_catalogs() -> None:
	for row in category_rows():
		values = dict(row)
		label = values.pop("label")
		code = str(values["code"])
		_upsert(
			"NXR Economic Category",
			code,
			{**values, "category_name": label, "active": 1, "system_managed": 1},
		)
	for row in operation_rows():
		values = dict(row)
		label = values.pop("label")
		code = str(values["code"])
		_upsert(
			"NXR Operation Type",
			code,
			{**values, "operation_name": label, "active": 1, "system_managed": 1},
		)
