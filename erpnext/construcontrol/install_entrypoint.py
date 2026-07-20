from __future__ import annotations

import os
from datetime import date
from typing import Any


def _run_construcontrol_install() -> None:
	"""Run migration-backed setup in the same guarded context used by Frappe."""
	import frappe

	from erpnext.construcontrol.install import after_migrate

	had_flag = "in_migrate" in frappe.flags
	previous = frappe.flags.get("in_migrate")
	frappe.flags["in_migrate"] = True
	try:
		after_migrate()
	finally:
		if had_flag:
			frappe.flags["in_migrate"] = previous
		else:
			frappe.flags.pop("in_migrate", None)


def _setup_arguments() -> dict[str, Any]:
	"""Return deterministic, non-demo defaults for the private ConstruControl site."""
	current_year = date.today().year
	company_name = os.environ.get("CONSTRUCONTROL_COMPANY_NAME", "ConstruControl").strip()
	company_abbr = os.environ.get("CONSTRUCONTROL_COMPANY_ABBR", "CC").strip().upper()
	country = os.environ.get("CONSTRUCONTROL_COUNTRY", "Honduras").strip()
	currency = os.environ.get("CONSTRUCONTROL_CURRENCY", "HNL").strip().upper()
	timezone = os.environ.get("TZ", "America/Tegucigalpa").strip()

	for label, value in {
		"company name": company_name,
		"company abbreviation": company_abbr,
		"country": country,
		"currency": currency,
		"timezone": timezone,
	}.items():
		if not value:
			raise RuntimeError(f"ConstruControl setup requires a non-empty {label}.")

	return {
		"language": "English",
		"country": country,
		"timezone": timezone,
		"currency": currency,
		"full_name": "Administrator",
		"email": "",
		"company_name": company_name,
		"company_abbr": company_abbr,
		"chart_of_accounts": "Standard",
		"fy_start_date": f"{current_year}-01-01",
		"fy_end_date": f"{current_year}-12-31",
		"domain": "Services",
		"setup_demo": 0,
		"enable_telemetry": 0,
	}


def ensure_setup_complete() -> None:
	"""Complete Frappe/ERPNext setup synchronously and fail closed if it remains pending."""
	import frappe

	if frappe.is_setup_complete():
		print("[ConstruControl] Frappe/ERPNext setup already complete", flush=True)
		return

	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

	had_background_flag = "trigger_site_setup_in_background" in frappe.conf
	previous_background_flag = frappe.conf.get("trigger_site_setup_in_background")
	frappe.conf["trigger_site_setup_in_background"] = False
	try:
		result = setup_complete(_setup_arguments())
	finally:
		if had_background_flag:
			frappe.conf["trigger_site_setup_in_background"] = previous_background_flag
		else:
			frappe.conf.pop("trigger_site_setup_in_background", None)

	frappe.clear_cache()
	if not frappe.is_setup_complete():
		raise RuntimeError(
			"Frappe/ERPNext setup wizard returned without completing the site: " f"result={result!r}"
		)
	print("[ConstruControl] Frappe/ERPNext setup completed and verified", flush=True)


def after_install() -> None:
	"""Run ERPNext's official installer, ConstruControl setup and the official setup wizard."""
	from erpnext.setup.install import after_install as erpnext_after_install

	erpnext_after_install()
	_run_construcontrol_install()
	ensure_setup_complete()
