from __future__ import annotations

from collections.abc import Callable

import frappe

ROLES = (
    "ConstruControl Manager",
    "ConstruControl Auditor",
    "ConstruControl Operator",
    "ConstruControl Viewer",
)

EXPECTED_RUNTIME_PAGES = (
    "construcontrol-dashboard",
    "construcontrol-migration-console",
    "construcontrol-reporting-center",
    "construcontrol-weekly-closing",
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


def _validate_runtime_pages() -> None:
    missing = [name for name in EXPECTED_RUNTIME_PAGES if not frappe.db.exists("Page", name)]
    if missing:
        raise RuntimeError(
            "ConstruControl migration did not create the required runtime pages: " + ", ".join(missing)
        )


def _run_page_integrations_safely(*callbacks: Callable[[], None]) -> None:
    """Create all ConstruControl runtime pages without leaving developer mode enabled.

    Frappe v15 rejects insertion of new ``Page`` records when developer mode is
    disabled. ConstruControl creates four non-standard database-backed pages from
    validated bundled definitions during ``after_migrate``. Enable the in-process
    flag only while the three page-producing installers run, validate that every
    expected page exists, and always restore the exact production value.
    """
    original_developer_mode = getattr(frappe.conf, "developer_mode", 0)
    try:
        frappe.conf.developer_mode = 1
        for callback in callbacks:
            callback_name = getattr(callback, "__name__", repr(callback))
            print(f"[ConstruControl] after_migrate start: {callback_name}", flush=True)
            callback()
            print(f"[ConstruControl] after_migrate ok: {callback_name}", flush=True)
        _validate_runtime_pages()
        print("[ConstruControl] required runtime pages verified", flush=True)
    finally:
        frappe.conf.developer_mode = original_developer_mode


def after_migrate() -> None:
    """Install the operational extension without replacing ERPNext core data."""
    _ensure_roles()

    from erpnext.construcontrol.integration import ensure_operational_integration
    from erpnext.construcontrol.permissions import enforce_critical_permissions
    from erpnext.construcontrol.reporting_install import ensure_reporting_integration
    from erpnext.construcontrol.weekly_install import ensure_weekly_integration
    from erpnext.construcontrol.workspace_cleanup import consolidate_integration_workspaces

    _run_page_integrations_safely(
        ensure_operational_integration,
        ensure_reporting_integration,
        ensure_weekly_integration,
    )
    enforce_critical_permissions()
    _apply_safe_settings()
    consolidate_integration_workspaces()
    frappe.clear_cache()
    print("[ConstruControl] after_migrate completed", flush=True)
