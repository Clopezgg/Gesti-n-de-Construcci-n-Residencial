#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []

required = (
    "erpnext/construcontrol/api.py",
    "erpnext/construcontrol/audit.py",
    "erpnext/construcontrol/controllers.py",
    "erpnext/construcontrol/install.py",
    "erpnext/construcontrol/integration.py",
    "erpnext/construcontrol/permissions.py",
    "erpnext/construcontrol/reporting.py",
    "erpnext/construcontrol/reporting_install.py",
    "erpnext/construcontrol/weekly.py",
    "erpnext/construcontrol/weekly_install.py",
    "erpnext/construcontrol/workspace_cleanup.py",
    "erpnext/construcontrol/migration/normalization.py",
    "erpnext/construcontrol/migration/native_records.py",
    "erpnext/construcontrol/storage/supabase.py",
    "erpnext/construcontrol/tests/test_normalization_standalone.py",
    "erpnext/public/css/construcontrol.css",
    "erpnext/public/js/construcontrol_mobile.js",
    "erpnext/public/construcontrol/manifest.webmanifest",
    "erpnext/public/construcontrol/icon.svg",
    "docs/deployment/AWS_COOLIFY.md",
)
for relative in required:
    if not (ROOT / relative).is_file():
        errors.append(f"Missing completion asset: {relative}")


def text(relative: str) -> str:
    path = ROOT / relative
    return path.read_text(encoding="utf-8") if path.exists() else ""


hooks = text("erpnext/hooks.py")
for phrase in (
    "erpnext.construcontrol.audit.record_event",
    "/assets/erpnext/css/construcontrol.css",
    "/assets/erpnext/js/construcontrol_mobile.js",
):
    if phrase not in hooks:
        errors.append(f"erpnext/hooks.py does not load required integration: {phrase}")

install = text("erpnext/construcontrol/install.py")
for phrase in (
    "ensure_operational_integration",
    "ensure_reporting_integration",
    "ensure_weekly_integration",
    "enforce_critical_permissions",
    "consolidate_integration_workspaces",
):
    if phrase not in install:
        errors.append(f"after_migrate does not enforce: {phrase}")

api = text("erpnext/construcontrol/api.py")
for phrase in (
    "_require_system_manager",
    "is_private",
    "_create_database_backup",
    "_cleanup_demo_data",
    '"images_imported": 0',
    "source_sha != validated_run.source_sha256",
):
    if phrase not in api:
        errors.append(f"Migration API is missing safety behavior: {phrase}")

storage = text("erpnext/construcontrol/storage/supabase.py")
for phrase in (
    "_validated_supabase_url",
    'parsed.scheme != "https"',
    'hostname.endswith(".supabase.co")',
    'frappe.session.user == "Guest"',
    'file_doc.has_permission("read")',
):
    if phrase not in storage:
        errors.append(f"Storage security is missing: {phrase}")

importer = text("erpnext/construcontrol/migration/importer.py")
for phrase in (
    "normalize_role",
    "normalize_movement_type",
    "resolve_actor_identity",
    "in_construcontrol_migration",
    "_deduplicate_user_access",
    "ensure_item",
    "ensure_supplier",
):
    if phrase not in importer:
        errors.append(f"Production importer is missing normalization or native mapping: {phrase}")

native = text("erpnext/construcontrol/migration/native_records.py")
for phrase in (
    "Materiales de Construcción",
    "Proveedores de Construcción",
    "is_sales_item",
    "_deleted",
):
    if phrase not in native:
        errors.append(f"Native construction master mapping is missing: {phrase}")

controllers = text("erpnext/construcontrol/controllers.py")
for phrase in (
    "El gasto supera el saldo",
    "OUTGOING_MOVEMENTS",
    "La salida de {0} supera la existencia",
    "recalculate_funding_source",
    "recalculate_contract",
):
    if phrase not in controllers:
        errors.append(f"Operational validation is missing: {phrase}")

reporting = text("erpnext/construcontrol/reporting.py")
for phrase in (
    "get_reporting_summary",
    "generate_report_record",
    "prepare_notification",
    "mark_notification_sent",
    "authorized",
):
    if phrase not in reporting:
        errors.append(f"BI01 reporting or notification flow is missing: {phrase}")

weekly = text("erpnext/construcontrol/weekly.py")
for phrase in (
    "preview_weekly_closing",
    "create_weekly_closing",
    "initial_balance_hnl",
    "final_balance_hnl",
    "Ya existe un cierre activo",
):
    if phrase not in weekly:
        errors.append(f"CL01 weekly closing flow is missing: {phrase}")

permissions = text("erpnext/construcontrol/permissions.py")
for doctype in (
    "ConstruControl Migration Run",
    "ConstruControl Legacy Record",
    "CC User Access",
    "CC Audit Log",
    "CC Generated Report",
    "CC Notification Contact",
    "CC Notification Rule",
    "CC Notification Log",
):
    if doctype not in permissions:
        errors.append(f"Critical permissions do not cover {doctype}")

workspace = json.loads(text("erpnext/construcontrol/workspace/construcontrol/construcontrol.json") or "{}")
labels = [str(row.get("label") or "") for row in workspace.get("links", [])]
for required_label in (
    "FI01 · Ingresos, remesas y aportes",
    "FI02 · Gastos y facturas",
    "CO01 · Contratos",
    "PR01 · Fases de obra",
    "MM01 · Materiales",
    "MIGO · Movimientos de inventario",
    "QC01 · Avance de obra",
    "CL01 · Crear cierre semanal",
    "CL01 · Historial de cierres",
    "BI01 · Reportes y notificaciones",
    "AU01 · Auditoría",
    "US01 · Usuarios y acceso",
    "AD01 · Evidencias y archivos",
):
    if labels.count(required_label) != 1:
        errors.append(f"Workspace link must exist exactly once: {required_label}")
if any(label.casefold() == "integraciones next" for label in labels):
    errors.append("ConstruControl workspace still exposes Integraciones NEXT")

manifest = json.loads(text("erpnext/public/construcontrol/manifest.webmanifest") or "{}")
if manifest.get("start_url") != "/app/construcontrol-dashboard":
    errors.append("PWA manifest has an incorrect ConstruControl start_url")
if manifest.get("display") != "standalone":
    errors.append("PWA manifest must use standalone display")

mobile = text("erpnext/public/js/construcontrol_mobile.js")
for phrase in ("cc-mobile-nav", "cc-offline-banner", "get_current_identity", "System Manager"):
    if phrase not in mobile:
        errors.append(f"Mobile shell is missing: {phrase}")

manual = text("MANUAL_PASO_A_PASO.md")
for phrase in (
    "AWS EC2",
    "Security Group",
    "Docker Compose Location: /docker-compose.yml",
    "ConstruControl Settings",
    "Migrar y limpiar demo",
    "restauración",
):
    if phrase not in manual:
        errors.append(f"Production manual is missing exact instruction: {phrase}")

marker = re.compile(r"\b(?:TODO|FIXME|IMPLEMENTAR DESPU[EÉ]S|PENDIENTE DE IMPLEMENTAR)\b", re.I)
for path in (ROOT / "erpnext" / "construcontrol").rglob("*"):
    if path.is_file() and path.suffix.lower() in {".py", ".js", ".json", ".md"}:
        if marker.search(path.read_text(encoding="utf-8", errors="ignore")):
            errors.append(f"Unresolved implementation marker in {path.relative_to(ROOT)}")

# Search only the ConstruControl-owned files. ERPNext upstream intentionally ships
# its own demo fixtures, which are removed from production by the official cleanup.
demo_names = re.compile(r"\b(?:Sneakers|Coffee Mug|Television|Grant Plastics|Zuckerman Security)\b", re.I)
demo_scan_paths = [
    ROOT / "erpnext" / "construcontrol",
    ROOT / "erpnext" / "public" / "css" / "construcontrol.css",
    ROOT / "erpnext" / "public" / "js" / "construcontrol_mobile.js",
    ROOT / "erpnext" / "public" / "construcontrol",
]
for base in demo_scan_paths:
    paths = [base] if base.is_file() else list(base.rglob("*")) if base.exists() else []
    for path in paths:
        if path.is_file() and path.suffix.lower() in {".py", ".js", ".json", ".css", ".md", ".webmanifest", ".svg"}:
            if demo_names.search(path.read_text(encoding="utf-8", errors="ignore")):
                errors.append(f"ConstruControl extension contains demo retail data: {path.relative_to(ROOT)}")

print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2))
raise SystemExit(0 if not errors else 1)
