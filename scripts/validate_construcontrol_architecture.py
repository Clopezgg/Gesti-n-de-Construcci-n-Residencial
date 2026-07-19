#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs" / "architecture" / "FASE_1_AUDITORIA_Y_ARQUITECTURA.md"
TARGET = ROOT / "docs" / "architecture" / "ARQUITECTURA_OBJETIVO_CONSTRUCONTROL.md"
INVENTORY = ROOT / "docs" / "architecture" / "module_inventory.json"
WORKSPACE = ROOT / "erpnext" / "construcontrol" / "workspace" / "construcontrol" / "construcontrol.json"

errors: list[str] = []

for path in (AUDIT, TARGET, INVENTORY, WORKSPACE):
    if not path.is_file():
        errors.append(f"Missing architecture source: {path.relative_to(ROOT)}")

if errors:
    print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
    raise SystemExit(1)

inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
workspace = json.loads(WORKSPACE.read_text(encoding="utf-8"))
audit_text = AUDIT.read_text(encoding="utf-8")
target_text = TARGET.read_text(encoding="utf-8")

if inventory.get("product") != "ConstruControl":
    errors.append("Architecture inventory product must be ConstruControl")
if inventory.get("source_of_truth", {}).get("branch") != "main":
    errors.append("Architecture inventory must declare main as production source of truth")

required_guardrails = {
    "No eliminar volúmenes Docker",
    "No ejecutar docker compose down -v",
    "No realizar cambios permanentes únicamente en AWS o Coolify",
    "No guardar secretos en GitHub",
    "Toda migración de esquema debe ser idempotente",
}
actual_guardrails = set(inventory.get("infrastructure_guardrails") or [])
missing_guardrails = sorted(required_guardrails - actual_guardrails)
if missing_guardrails:
    errors.append("Missing infrastructure guardrails: " + ", ".join(missing_guardrails))

modules = inventory.get("modules") or []
if not isinstance(modules, list) or len(modules) < 17:
    errors.append("Module inventory must contain the complete ConstruControl product surface")

required_codes = {
    "CC00",
    "FI01",
    "FI02",
    "AP01",
    "CO01",
    "PR01",
    "MM01",
    "MIGO",
    "MM02",
    "QC01",
    "CL01",
    "BI01",
    "AU01",
    "US01",
    "INT01",
    "AD01",
    "MIG",
}
seen_codes: set[str] = set()
seen_targets: set[str] = set()
for module in modules:
    code = str(module.get("code") or "").strip()
    target = str(module.get("current_target") or "").strip()
    owner_phase = module.get("owner_phase")
    if not code:
        errors.append("Module without code")
        continue
    if code in seen_codes:
        errors.append(f"Duplicate module code: {code}")
    seen_codes.add(code)
    if target:
        if target in seen_targets:
            errors.append(f"Duplicate module target: {target}")
        seen_targets.add(target)
    if not isinstance(owner_phase, int) or owner_phase < 2 or owner_phase > 12:
        errors.append(f"Invalid owner phase for {code}: {owner_phase}")
    if module.get("shell_required") is not True:
        errors.append(f"Module is not covered by the unified shell contract: {code}")

missing_codes = sorted(required_codes - seen_codes)
if missing_codes:
    errors.append("Missing required product modules: " + ", ".join(missing_codes))

workspace_targets = {
    f"{row.get('link_type')}:{row.get('link_to')}"
    for row in workspace.get("links", [])
    if row.get("link_type") in {"DocType", "Page"} and row.get("link_to")
}
registered_targets = set(seen_targets)
unregistered_workspace_targets = sorted(workspace_targets - registered_targets)
# Some operational/admin links intentionally share a future phase even when they
# do not yet have their own top-level navigation card. They still must be listed
# here explicitly so additions cannot silently escape the architecture review.
allowed_secondary_targets = {
    "DocType:CC Weekly Closing",
    "DocType:CC Business Partner Profile",
    "DocType:CC Equipment Control",
    "DocType:CC Change Order",
    "DocType:CC Approval Request",
    "DocType:CC Generated Report",
    "DocType:CC Notification Contact",
    "DocType:CC Notification Rule",
    "DocType:CC Notification Log",
    "DocType:ConstruControl Migration Run",
    "DocType:ConstruControl Legacy Record",
    "DocType:ConstruControl Settings",
}
unregistered_workspace_targets = sorted(set(unregistered_workspace_targets) - allowed_secondary_targets)
if unregistered_workspace_targets:
    errors.append("Workspace targets missing architecture ownership: " + ", ".join(unregistered_workspace_targets))

for phrase in (
    "ERPNext/Frappe permanece como motor interno",
    "No se dará una fase por completada con pruebas fallidas",
    "Datos productivos modificados: **ninguno**",
):
    if phrase not in audit_text:
        errors.append(f"Phase 1 audit is missing binding statement: {phrase}")

for phrase in (
    "ConstruControl es el producto visible",
    "Contrato de navegación",
    "Contrato financiero",
    "Contrato de PWA",
    "Estrategia de evolución sin dañar producción",
):
    if phrase not in target_text:
        errors.append(f"Target architecture is missing contract: {phrase}")

result = {
    "ok": not errors,
    "modules": len(modules),
    "required_codes_present": not missing_codes,
    "workspace_targets_reviewed": len(workspace_targets),
    "guardrails_present": not missing_guardrails,
    "errors": errors,
}
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if not errors else 1)
