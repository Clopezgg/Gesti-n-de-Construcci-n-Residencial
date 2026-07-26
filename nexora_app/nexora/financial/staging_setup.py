from __future__ import annotations

import frappe


DEMO_COMPANY = "NEXORA Staging"
DEMO_COMPANY_ABBR = "NXS"


def ensure_demo_company() -> str:
	"""Ensure isolated staging has the ERPNext company required by Project."""
	if not bool(frappe.conf.get("nexora_staging")):
		frappe.throw("ensure_demo_company is restricted to nexora_staging sites")

	company = frappe.db.get_single_value("Global Defaults", "default_company")
	if not company:
		company = frappe.db.get_value("Company", {}, "name", order_by="creation asc")
	if not company:
		company = (
			frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": DEMO_COMPANY,
					"abbr": DEMO_COMPANY_ABBR,
					"default_currency": "HNL",
					"country": "Honduras",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	frappe.db.set_single_value("Global Defaults", "default_company", company)
	frappe.defaults.set_global_default("company", company)
	frappe.db.commit()
	return str(company)
