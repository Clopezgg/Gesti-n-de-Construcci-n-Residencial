from __future__ import annotations

import frappe

ROLES = (
    "ConstruControl Manager",
    "ConstruControl Auditor",
    "ConstruControl Operator",
    "ConstruControl Viewer",
)


def _ensure_roles() -> None:
    for role_name in ROLES:
        if not frappe.db.exists("Role", role_name):
            frappe.get_doc(
                {
                    "doctype": "Role",
                    "role_name": role_name,
                    "desk_access": 1,
                }
            ).insert(ignore_permissions=True)


def _apply_safe_settings() -> None:
    settings = frappe.get_single("ConstruControl Settings")
    changed = False
    safe_defaults = {
        "require_backup_before_import": 1,
        "cleanup_demo_after_migration": 1,
        "import_evidence_files": 0,
    }
    for fieldname, value in safe_defaults.items():
        if not settings.meta.has_field(fieldname):
            continue
        current = settings.get(fieldname)
        if current in (None, ""):
            settings.set(fieldname, value)
            changed = True

    # Historical photographs are deliberately excluded from this migration.
    if settings.meta.has_field("import_evidence_files") and settings.import_evidence_files:
        settings.import_evidence_files = 0
        changed = True

    if changed:
        settings.save(ignore_permissions=True)


def after_migrate() -> None:
    """Install the operational extension without replacing ERPNext core data."""
    _ensure_roles()

    from erpnext.construcontrol.integration import ensure_operational_integration
    from erpnext.construcontrol.permissions import enforce_critical_permissions
    from erpnext.construcontrol.reporting_install import ensure_reporting_integration
    from erpnext.construcontrol.workspace_cleanup import consolidate_integration_workspaces

    ensure_operational_integration()
    ensure_reporting_integration()
    enforce_critical_permissions()
    _apply_safe_settings()
    consolidate_integration_workspaces()
    frappe.clear_cache()
