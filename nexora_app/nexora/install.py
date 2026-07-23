from __future__ import annotations

import frappe
from frappe import _

from nexora.financial.seeds import seed_analytic_catalogs
from nexora.patches.v0_1.create_sequence_counter import execute as create_sequence_counter

BASE_ROLES = (
	"NEXORA Administrator",
	"NEXORA Finance Manager",
	"NEXORA Finance Operator",
	"NEXORA Auditor",
	"NEXORA Project Viewer",
)


def _ensure_sequence_counter() -> None:
	"""Create the native global counter in the install-safe lifecycle."""
	create_sequence_counter()


def _ensure_clean_site_reference_data() -> None:
	if not frappe.db.exists("Currency", "HNL"):
		frappe.get_doc(
			{
				"doctype": "Currency",
				"currency_name": "HNL",
				"enabled": 1,
				"fraction": "Centavo",
				"fraction_units": 100,
				"symbol": "L",
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Country", "Honduras"):
		frappe.get_doc({"doctype": "Country", "country_name": "Honduras", "code": "HN"}).insert(
			ignore_permissions=True
		)


def after_install() -> None:
	"""Install only clean-site identities and the native sequence counter."""
	_ensure_sequence_counter()
	_ensure_clean_site_reference_data()
	for role_name in BASE_ROLES:
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1}).insert(
				ignore_permissions=True
			)


def after_migrate() -> None:
	"""Seed catalogs after Frappe has synchronized the canonical NEXORA DocTypes."""
	seed_analytic_catalogs()


def before_uninstall() -> None:
	"""Refuse destructive rollback when the site already contains NEXORA operations."""
	if frappe.db.exists("DocType", "NXR Operation") and frappe.db.count("NXR Operation"):
		frappe.throw(
			_(
				"NEXORA contiene operaciones. Exporte evidencia y ejecute un rollback documentado antes de desinstalar."
			),
			title=_("Desinstalación bloqueada"),
		)


def after_uninstall() -> None:
	"""Remove only unassigned NEXORA roles; never touch ERPNext or legacy records."""
	for role_name in BASE_ROLES:
		assigned = frappe.db.exists("Has Role", {"role": role_name})
		if not assigned and frappe.db.exists("Role", role_name):
			frappe.delete_doc("Role", role_name, ignore_permissions=True, force=True)
