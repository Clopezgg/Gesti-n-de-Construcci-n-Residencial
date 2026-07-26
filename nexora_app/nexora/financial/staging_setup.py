from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime

DEMO_COMPANY = "NEXORA Staging"
DEMO_COMPANY_ABBR = "NXS"
REQUIRED_WAREHOUSE_TYPES = ("Transit",)
STAGING_ADMIN_USER = "Administrator"
STAGING_ADMIN_ROLE = "NEXORA Administrator"


def _ensure_erpnext_prerequisites() -> str:
	"""Create standard ERPNext setup rows required by Company and Desk bootstrap."""
	for warehouse_type in REQUIRED_WAREHOUSE_TYPES:
		if not frappe.db.exists("Warehouse Type", warehouse_type):
			frappe.get_doc(
				{
					"doctype": "Warehouse Type",
					"name": warehouse_type,
					"warehouse_type": warehouse_type,
				}
			).insert(ignore_permissions=True)

	current_year = now_datetime().year
	fiscal_year = str(current_year)
	if not frappe.db.exists("Fiscal Year", fiscal_year):
		frappe.get_doc(
			{
				"doctype": "Fiscal Year",
				"year": fiscal_year,
				"year_start_date": f"{current_year}-01-01",
				"year_end_date": f"{current_year}-12-31",
			}
		).insert(ignore_permissions=True)
	frappe.defaults.set_global_default("fiscal_year", fiscal_year)
	return fiscal_year


def _ensure_staging_administrator_access() -> None:
	"""Grant the isolated browser-test administrator explicit NEXORA Page access."""
	if not frappe.db.exists("User", STAGING_ADMIN_USER):
		frappe.throw(_("No existe el usuario administrador requerido para validar NEXORA."))
	if frappe.db.exists(
		"Has Role",
		{"parent": STAGING_ADMIN_USER, "parenttype": "User", "role": STAGING_ADMIN_ROLE},
	):
		return
	user = frappe.get_doc("User", STAGING_ADMIN_USER)
	user.append("roles", {"role": STAGING_ADMIN_ROLE})
	user.save(ignore_permissions=True)


def _complete_staging_setup() -> None:
	"""Mark the isolated staging site as configured so Frappe Desk can boot."""
	for app_name in frappe.get_all("Installed Application", pluck="app_name"):
		frappe.db.set_value(
			"Installed Application",
			{"app_name": app_name},
			"is_setup_complete",
			1,
			update_modified=False,
		)
	frappe.db.set_single_value("System Settings", "setup_complete", 1)
	frappe.db.set_default("desktop:home_page", "workspace")


def ensure_demo_company() -> str:
	"""Ensure isolated staging has the ERPNext company required by Project and Desk."""
	if not bool(frappe.conf.get("nexora_staging")):
		frappe.throw(_("La preparación de la compañía exige un sitio NEXORA de staging."))

	_ensure_erpnext_prerequisites()
	_ensure_staging_administrator_access()
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
					"create_chart_of_accounts_based_on": "Standard Template",
					"chart_of_accounts": "Standard",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	frappe.db.set_single_value("Global Defaults", "default_company", company)
	frappe.defaults.set_global_default("company", company)
	_complete_staging_setup()
	return str(company)
