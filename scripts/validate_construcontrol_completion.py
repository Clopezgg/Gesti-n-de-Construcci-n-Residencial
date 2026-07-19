#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []


def text(relative: str) -> str:
    path = ROOT / relative
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def require_file(relative: str) -> None:
    path = ROOT / relative
    if not path.is_file() or path.stat().st_size == 0:
        errors.append(f"Missing completion asset: {relative}")


def require_phrases(relative: str, phrases: tuple[str, ...], label: str) -> None:
    source = text(relative)
    for phrase in phrases:
        if phrase not in source:
            errors.append(f"{label} is missing: {phrase}")


def function_source(relative: str, function_name: str) -> str:
    source = text(relative)
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        errors.append(f"Invalid Python syntax in {relative}: {exc}")
        return ""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return ast.get_source_segment(source, node) or ""
    return ""


required = (
    "erpnext/construcontrol/api.py",
    "erpnext/construcontrol/audit.py",
    "erpnext/construcontrol/business_rules.py",
    "erpnext/construcontrol/users.py",
    "erpnext/construcontrol/controllers.py",
    "erpnext/construcontrol/install.py",
    "erpnext/construcontrol/integration.py",
    "erpnext/construcontrol/permissions.py",
    "erpnext/construcontrol/finance.py",
    "erpnext/construcontrol/finance_setup.py",
    "erpnext/construcontrol/expenses.py",
    "erpnext/construcontrol/expense_setup.py",
    "erpnext/construcontrol/construction.py",
    "erpnext/construcontrol/executive.py",
    "erpnext/construcontrol/integrations.py",
    "erpnext/construcontrol/reporting.py",
    "erpnext/construcontrol/weekly.py",
    "erpnext/construcontrol/schema_specialization.py",
    "erpnext/construcontrol/migration/importer.py",
    "erpnext/construcontrol/migration/catalog_rules.py",
    "erpnext/construcontrol/migration/normalization.py",
    "erpnext/construcontrol/migration/native_records.py",
    "erpnext/construcontrol/page/construcontrol_dashboard/construcontrol_dashboard.js",
    "erpnext/construcontrol/page/construcontrol_project_center/construcontrol_project_center.js",
    "erpnext/construcontrol/page/construcontrol_users/construcontrol_users.js",
    "erpnext/construcontrol/page/construcontrol_integrations/construcontrol_integrations.js",
    "erpnext/public/css/construcontrol_canonical.css",
    "erpnext/public/js/construcontrol_mobile.js",
    "erpnext/public/construcontrol/manifest.webmanifest",
    "erpnext/public/construcontrol/apple-touch-icon-180.png",
    "erpnext/public/construcontrol/icon-192.png",
    "erpnext/public/construcontrol/icon-512.png",
    "docs/deployment/AWS_COOLIFY.md",
)
for relative in required:
    require_file(relative)

require_phrases(
    "erpnext/hooks.py",
    (
        "erpnext.construcontrol.audit.record_event",
        "/assets/erpnext/css/construcontrol_canonical.css",
        "/assets/erpnext/js/construcontrol_mobile.js",
        "erpnext.construcontrol.finance.validate_treasury_source",
        "erpnext.construcontrol.expenses.validate_professional_expense",
    ),
    "ERPNext hooks integration",
)

require_phrases(
    "erpnext/construcontrol/install.py",
    (
        "before the first database mutation",
        "ensure_operational_integration",
        "ensure_reporting_integration",
        "ensure_weekly_integration",
        "ensure_product_pages",
        "specialize_operational_doctypes",
        "ensure_finance_configuration",
        "ensure_expense_fields",
        "enforce_critical_permissions",
        "consolidate_integration_workspaces",
        "record_runtime_contract",
        "construcontrol-users",
    ),
    "after_migrate",
)

require_phrases(
    "erpnext/construcontrol/api.py",
    (
        "_require_system_manager",
        "is_private",
        "_create_database_backup",
        "_cleanup_demo_data",
        '"images_imported": 0',
        "source_sha != validated_run.source_sha256",
    ),
    "Migration API safety",
)

require_phrases(
    "erpnext/construcontrol/migration/importer.py",
    (
        "_exclusive_migration_lock",
        "normalize_role",
        "normalize_movement_type",
        "normalize_income_channel",
        "normalize_expense_state",
        "resolve_actor_identity",
        "in_construcontrol_migration",
        "_deduplicate_user_access",
        "ensure_item",
        "ensure_supplier",
        "_source_datetime",
    ),
    "Historical importer",
)

require_phrases(
    "erpnext/construcontrol/users.py",
    (
        "_require_management",
        '"User"',
        '"Has Role"',
        '"User Permission"',
        "save_user",
        "set_user_enabled",
        "Solo un administrador del sistema puede asignar el rol ADMIN",
    ),
    "Native user administration",
)

require_phrases(
    "erpnext/construcontrol/finance.py",
    (
        "net_hnl = net * rate",
        "supports_remittance",
        "supports_deposit",
        "supports_transfer",
        "reconciliation == \"reconciled\"",
    ),
    "FI01 treasury control",
)
require_phrases(
    "erpnext/construcontrol/finance_setup.py",
    ("backfill_treasury_sources", '"OTHER"', "seed_financial_institutions"),
    "FI01 historical reconciliation",
)
require_phrases(
    "erpnext/construcontrol/expenses.py",
    (
        "backfill_professional_expenses",
        "sync_payable_from_expense",
        "_validate_duplicate_invoice",
        "rejection_reason",
        "balance_due_hnl",
    ),
    "FI02 expense control",
)
require_phrases(
    "erpnext/construcontrol/business_rules.py",
    ("normalize_expense_state", "expense_amounts", "normalize_income_channel"),
    "Canonical financial rules",
)

project_read = function_source("erpnext/construcontrol/construction.py", "get_project_center")
if not project_read:
    errors.append("Project center read service is missing")
elif any(token in project_read for token in (".save(", "db.set_value", ".insert(", "delete_doc")):
    errors.append("Project center read service still mutates data")
require_phrases(
    "erpnext/construcontrol/construction.py",
    ("_calculate_project_control", "persist=False", "expense_amounts", "delayed_phase_count"),
    "Project control",
)

require_phrases(
    "erpnext/construcontrol/executive.py",
    (
        "expense_total_hnl",
        "paid_hnl",
        "cash_available_hnl",
        "schedule_status_label",
        "action_label",
        "record_type_label",
        "alerts[:4]",
        "recent_activity",
    ),
    "Executive dashboard service",
)

dashboard = text("erpnext/construcontrol/page/construcontrol_dashboard/construcontrol_dashboard.js")
for forbidden in ("frappe.dom.freeze", "frappe.dom.unfreeze", "Módulos ConstruControl", "cc-module-grid"):
    if forbidden in dashboard:
        errors.append(f"Dashboard contains obsolete behavior: {forbidden}")
for required_phrase in ("slice(0, 3)", "alert?.route", "schedule_status_label", ".finally(() =>"):
    if required_phrase not in dashboard:
        errors.append(f"Dashboard is missing compact/actionable behavior: {required_phrase}")

project_page = text("erpnext/construcontrol/page/construcontrol_project_center/construcontrol_project_center.js")
for forbidden in ("frappe.dom.freeze", "frappe.dom.unfreeze"):
    if forbidden in project_page:
        errors.append(f"Project center contains global freeze: {forbidden}")

mobile = text("erpnext/public/js/construcontrol_mobile.js")
for phrase in (
    "cc-desktop-sidebar",
    "cc-app-topbar",
    "cc-mobile-nav",
    "cc-more-toggle",
    "cc-more-sheet",
    "cc-close-view",
    "construcontrol-dashboard",
    "construcontrol-profile",
    "construcontrol-users",
    "construcontrol-integrations",
    "System Manager",
):
    if phrase not in mobile:
        errors.append(f"Canonical shell is missing: {phrase}")
for forbidden in ("Integraciones NEXT", "CC User Access", '["Workspace"'):
    if forbidden in mobile:
        errors.append(f"Canonical navigation exposes obsolete route: {forbidden}")

responsive_css = text("erpnext/public/css/construcontrol_canonical.css")
for phrase in (
    "body.cc-construcontrol-route > .navbar",
    "cc-desktop-sidebar",
    "cc-app-topbar",
    "cc-mobile-nav",
    "cc-more-grid",
    "cc-more-backdrop",
    "safe-area-inset-bottom",
    "cc-executive-grid",
    "cc-users-page",
):
    if phrase not in responsive_css:
        errors.append(f"Canonical responsive behavior is missing: {phrase}")

manifest = json.loads(text("erpnext/public/construcontrol/manifest.webmanifest") or "{}")
if manifest.get("start_url") != "/app/construcontrol-dashboard":
    errors.append("PWA manifest has an incorrect ConstruControl start_url")
if manifest.get("display") != "standalone":
    errors.append("PWA manifest must use standalone display")
icon_sizes = {row.get("sizes") for row in manifest.get("icons", [])}
if not {"192x192", "512x512"}.issubset(icon_sizes):
    errors.append("PWA manifest is missing required PNG icons")

require_phrases(
    "erpnext/construcontrol/reporting.py",
    ("get_reporting_summary", "generate_report_record", "prepare_notification", "mark_notification_sent", "authorized"),
    "BI01 reporting flow",
)
require_phrases(
    "erpnext/construcontrol/weekly.py",
    ("preview_weekly_closing", "create_weekly_closing", "initial_balance_hnl", "final_balance_hnl", "Ya existe un cierre activo"),
    "CL01 weekly closing flow",
)
require_phrases(
    "erpnext/construcontrol/integrations.py",
    ("create_custom_integration", "archive_custom_integration", "delete_custom_integration", "credential_secret", "is_protected"),
    "Integration lifecycle",
)

manual = text("MANUAL_PASO_A_PASO.md")
for phrase in ("AWS EC2", "Security Group", "Docker Compose Location: /docker-compose.yml", "ConstruControl Settings", "Migrar y limpiar demo", "restauración"):
    if phrase not in manual:
        errors.append(f"Production manual is missing exact instruction: {phrase}")

marker = re.compile(r"\b(?:TODO|FIXME|IMPLEMENTAR DESPU[EÉ]S|PENDIENTE DE IMPLEMENTAR)\b", re.I)
for path in (ROOT / "erpnext" / "construcontrol").rglob("*"):
    if path.is_file() and path.suffix.lower() in {".py", ".js", ".json", ".md"}:
        if marker.search(path.read_text(encoding="utf-8", errors="ignore")):
            errors.append(f"Unresolved implementation marker in {path.relative_to(ROOT)}")

print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2))
raise SystemExit(0 if not errors else 1)
