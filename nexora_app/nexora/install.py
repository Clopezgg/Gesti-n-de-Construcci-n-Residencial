from __future__ import annotations

import frappe
from frappe import _

from nexora.patches.v0_1.create_sequence_counter import execute as create_sequence_counter

BASE_ROLES = (
    "NEXORA Administrator",
    "NEXORA Finance Manager",
    "NEXORA Finance Operator",
    "NEXORA Auditor",
    "NEXORA Project Viewer",
)


def after_install() -> None:
    """Install only the minimum clean-site identities required by NEXORA."""
    create_sequence_counter()
    for role_name in BASE_ROLES:
        if not frappe.db.exists("Role", role_name):
            frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1}).insert(
                ignore_permissions=True
            )
    frappe.db.commit()


def before_uninstall() -> None:
    """Refuse destructive rollback when the site already contains NEXORA operations."""
    if frappe.db.exists("DocType", "NXR Operation") and frappe.db.count("NXR Operation"):
        frappe.throw(
            _("NEXORA contiene operaciones. Exporte evidencia y ejecute un rollback documentado antes de desinstalar."),
            title=_("Desinstalación bloqueada"),
        )


def after_uninstall() -> None:
    """Remove only unassigned NEXORA roles; never touch ERPNext or legacy records."""
    for role_name in BASE_ROLES:
        assigned = frappe.db.exists("Has Role", {"role": role_name})
        if not assigned and frappe.db.exists("Role", role_name):
            frappe.delete_doc("Role", role_name, ignore_permissions=True, force=True)
    frappe.db.commit()
