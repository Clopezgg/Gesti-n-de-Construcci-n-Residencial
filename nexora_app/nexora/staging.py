from __future__ import annotations

import frappe


DEMO_COMPANY_NAME = "NEXORA Staging"
DEMO_COMPANY_ABBR = "NXS"
DEMO_COMPANY_CURRENCY = "HNL"
DEMO_COMPANY_COUNTRY = "Honduras"


def ensure_default_company() -> str:
	"""Ensure isolated staging sites have one deterministic ERPNext company."""
	if str(frappe.conf.get("nexora_staging") or "").strip() not in {"1", "true", "True"}:
		frappe.throw("Staging company bootstrap requires nexora_staging=1")

	company = frappe.db.get_value("Company", {}, "name", order_by="creation asc")
	if not company:
		company = (
			frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": DEMO_COMPANY_NAME,
					"abbr": DEMO_COMPANY_ABBR,
					"default_currency": DEMO_COMPANY_CURRENCY,
					"country": DEMO_COMPANY_COUNTRY,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	frappe.db.set_default("company", company)
	if frappe.db.exists("DocType", "Global Defaults"):
		frappe.db.set_single_value("Global Defaults", "default_company", company)
	frappe.db.commit()
	return str(company)
