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
    "erpnext/construcontrol/workspace_cleanup.py",
    "erpnext/construcontrol/migration/normalization.py",
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
for phrase in ("ensure_operational_integration", "enforce_critical_permissions", "consolidate_integration_workspaces"):
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

importer = text("erpnext/construcontrol/migration/importer.py")
for phrase in (
    "normalize_role",
    "normalize_movement_type",
    "resolve_actor_identity",
    "in_construcontrol_migration",
    "_deduplicate_user_access",
):
    if phrase not in importer:
        errors.append(f"Production importer is missing normalization: {phrase}")

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

permissions = text("erpnext/construcontrol/permissions.py")
for doctype in (
    "ConstruControl Migration Run",
    "ConstruControl Legacy Record",
    "CC User Access",
    "CC Audit Log",
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
    "CL01 · Cierres semanales",
    "AU01 · Auditoría",
    "US01 · Usuarios y acceso",
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

# Required business code must not contain unresolved implementation markers.
marker = re.compile(r"\b(?:TODO|FIXME|IMPLEMENTAR DESPU[EÉ]S|PENDIENTE DE IMPLEMENTAR)\b", re.I)
for path in (ROOT / "erpnext" / "construcontrol").rglob("*"):
    if path.is_file() and path.suffix.lower() in {".py", ".js", ".json", ".md"}:
        content = path.read_text(encoding="utf-8", errors="ignore")
        if marker.search(content):
            errors.append(f"Unresolved implementation marker in {path.relative_to(ROOT)}")

# Demo retail names must not be introduced by the ConstruControl extension.
demo_names = re.compile(r"\b(?:Sneakers|Coffee Mug|Television|Grant Plastics|Zuckerman Security)\b", re.I)
for base in (ROOT / "erpnext" / "construcontrol", ROOT / "erpnext" / "public"):
    for path in base.rglob("*") if base.exists() else []:
        if path.is_file() and path.suffix.lower() in {".py", ".js", ".json", ".css", ".md"}:
            if demo_names.search(path.read_text(encoding="utf-8", errors="ignore")):
                errors.append(f"ConstruControl extension contains demo retail data: {path.relative_to(ROOT)}")

print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2))
raise SystemExit(0 if not errors else 1)
