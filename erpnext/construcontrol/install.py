from __future__ import annotations

import frappe

ROLES = ("ConstruControl Manager", "ConstruControl Auditor", "ConstruControl Operator", "ConstruControl Viewer")


def after_migrate() -> None:
    """Install roles and the operational ConstruControl extension safely."""
    for role_name in ROLES:
        if not frappe.db.exists("Role", role_name):
            frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1}).insert(ignore_permissions=True)
    from erpnext.construcontrol.integration import ensure_operational_integration

    ensure_operational_integration()

    settings = frappe.get_single("ConstruControl Settings")
    changed = False
    safe_defaults = {
        "require_backup_before_import": 1,
        "cleanup_demo_after_migration": 1,
        "import_evidence_files": 0,
    }
    for fieldname, value in safe_defaults.items():
        current = settings.get(fieldname) if settings.meta.has_field(fieldname) else None
        if settings.meta.has_field(fieldname) and current in (None, ""):
            settings.set(fieldname, value); changed = True
    if settings.meta.has_field("import_evidence_files") and settings.import_evidence_files:
        settings.import_evidence_files = 0; changed = True
    if changed:
        settings.save(ignore_permissions=True)
