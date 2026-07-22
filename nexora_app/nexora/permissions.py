from __future__ import annotations

import frappe

ACCESS_ROLES = {
    "System Manager",
    "NEXORA Administrator",
    "NEXORA Finance Manager",
    "NEXORA Finance Operator",
    "NEXORA Auditor",
    "NEXORA Project Viewer",
}


def can_access_nexora() -> bool:
    if frappe.session.user == "Guest":
        return False
    return bool(ACCESS_ROLES.intersection(frappe.get_roles(frappe.session.user)))
