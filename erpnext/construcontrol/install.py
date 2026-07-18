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


def _upsert_runtime_page(*, name: str, title: str, script: str, roles: tuple[str, ...]) -> None:
    """Create or update a non-standard Page using database existence as truth.

    Frappe documents created with an explicit ``name`` can report a misleading
    ``is_new()`` state before insertion.  Never use that state to choose between
    ``save`` and ``insert``; use the database existence check captured before the
    document is built.
    """
    exists = bool(frappe.db.exists("Page", name))
    values = {
        "doctype": "Page",
        "name": name,
        "page_name": name,
        "title": title,
        "module": "ConstruControl",
        "standard": "No",
        "system_page": 0,
        "script": script,
    }

    if exists:
        page = frappe.get_doc("Page", name)
        for fieldname, value in values.items():
            if fieldname != "doctype":
                page.set(fieldname, value)
        page.set("roles", [])
    else:
        page = frappe.get_doc(values)

    for role in roles:
        page.append("roles", {"role": role})

    if exists:
        page.save(ignore_permissions=True)
    else:
        page.insert(ignore_permissions=True)


def _prime_auxiliary_runtime_pages() -> None:
    """Ensure pages with legacy installer persistence logic exist before updates."""
    from erpnext.construcontrol.reporting_install import PAGE_NAME as REPORTING_PAGE_NAME
    from erpnext.construcontrol.reporting_install import PAGE_SCRIPT as REPORTING_PAGE_SCRIPT
    from erpnext.construcontrol.weekly_install import PAGE_NAME as WEEKLY_PAGE_NAME
    from erpnext.construcontrol.weekly_install import PAGE_SCRIPT as WEEKLY_PAGE_SCRIPT

    _upsert_runtime_page(
        name=REPORTING_PAGE_NAME,
        title="BI01 · Reportes y notificaciones",
        script=REPORTING_PAGE_SCRIPT,
        roles=(
            "System Manager",
            "ConstruControl Manager",
            "ConstruControl Operator",
            "ConstruControl Auditor",
            "ConstruControl Viewer",
        ),
    )
    _upsert_runtime_page(
        name=WEEKLY_PAGE_NAME,
        title="CL01 · Cierre semanal",
        script=WEEKLY_PAGE_SCRIPT,
        roles=(
            "System Manager",
            "ConstruControl Manager",
            "ConstruControl Operator",
        ),
    )


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
    flag only while the page-producing installers run, validate that every
    expected page exists, and always restore the exact production value.
    """
    original_developer_mode = getattr(frappe.conf, "developer_mode", 0)
    try:
        frappe.conf.developer_mode = 1
        print("[ConstruControl] priming auxiliary runtime pages", flush=True)
        _prime_auxiliary_runtime_pages()
        print("[ConstruControl] auxiliary runtime pages ready", flush=True)

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
