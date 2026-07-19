from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

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
    "construcontrol-profile",
    "construcontrol-project-center",
    "construcontrol-integrations",
)


def _validate_runtime_definitions() -> dict[str, Any]:
    from erpnext.construcontrol.migration.runtime_contract import validate_runtime_contract_or_raise

    runtime_dir = Path(__file__).with_name("runtime")
    report = validate_runtime_contract_or_raise(runtime_dir)
    print(
        "[ConstruControl] runtime contract verified "
        f"v{report['contract_version']} "
        f"sha256={str(report['sha256'])[:16]} "
        f"doctypes={report['doctype_count']} assets={report['asset_count']}",
        flush=True,
    )
    for warning in report.get("warnings") or []:
        print(f"[ConstruControl] runtime contract warning: {warning}", flush=True)
    return report


def _ensure_roles() -> None:
    for role_name in ROLES:
        if not frappe.db.exists("Role", role_name):
            frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1}).insert(ignore_permissions=True)


def _apply_safe_settings() -> None:
    settings = frappe.get_single("ConstruControl Settings")
    changed = False
    for fieldname, value in {
        "require_backup_before_import": 1,
        "cleanup_demo_after_migration": 1,
        "import_evidence_files": 0,
    }.items():
        if settings.meta.has_field(fieldname) and settings.get(fieldname) != value:
            settings.set(fieldname, value)
            changed = True
    if changed:
        settings.save(ignore_permissions=True)
        print("[ConstruControl] mandatory migration safety settings enforced", flush=True)


def _validate_runtime_pages() -> None:
    missing = [name for name in EXPECTED_RUNTIME_PAGES if not frappe.db.exists("Page", name)]
    if missing:
        raise RuntimeError("ConstruControl migration did not create the required runtime pages: " + ", ".join(missing))


def _run_page_integrations_safely(*callbacks: Callable[[], None]) -> None:
    original_developer_mode = getattr(frappe.conf, "developer_mode", 0)
    original_in_import = getattr(frappe.flags, "in_import", False)
    try:
        frappe.conf.developer_mode = 1
        frappe.flags.in_import = True
        print("[ConstruControl] exact runtime page naming enabled", flush=True)
        for callback in callbacks:
            callback_name = getattr(callback, "__name__", repr(callback))
            print(f"[ConstruControl] after_migrate start: {callback_name}", flush=True)
            callback()
            print(f"[ConstruControl] after_migrate ok: {callback_name}", flush=True)
        _validate_runtime_pages()
        print("[ConstruControl] required runtime pages verified", flush=True)
    finally:
        frappe.flags.in_import = original_in_import
        frappe.conf.developer_mode = original_developer_mode


def after_migrate() -> None:
    """Install the operational extension without replacing ERPNext core data."""
    runtime_report = _validate_runtime_definitions()
    _ensure_roles()

    from erpnext.construcontrol.construction_setup import ensure_construction_fields
    from erpnext.construcontrol.expense_setup import ensure_expense_fields
    from erpnext.construcontrol.finance_setup import ensure_finance_configuration
    from erpnext.construcontrol.integration import ensure_operational_integration
    from erpnext.construcontrol.integration_setup import seed_integration_registry
    from erpnext.construcontrol.permissions import enforce_critical_permissions
    from erpnext.construcontrol.product_pages import ensure_product_pages
    from erpnext.construcontrol.reporting_install import ensure_reporting_integration
    from erpnext.construcontrol.schema_state import record_runtime_contract
    from erpnext.construcontrol.weekly_install import ensure_weekly_integration
    from erpnext.construcontrol.workspace_cleanup import consolidate_integration_workspaces

    _run_page_integrations_safely(
        ensure_operational_integration,
        ensure_reporting_integration,
        ensure_weekly_integration,
        ensure_product_pages,
    )
    ensure_finance_configuration()
    ensure_expense_fields()
    ensure_construction_fields()
    seed_integration_registry()
    enforce_critical_permissions()
    _apply_safe_settings()
    consolidate_integration_workspaces()
    record_runtime_contract(runtime_report)
    frappe.clear_cache()
    print("[ConstruControl] after_migrate completed", flush=True)
