#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from generate_file_inventory import build_inventory, build_manifest

ROOT = Path(__file__).resolve().parents[1]
NEXORA_ARCHITECTURE = ROOT / "docs" / "nexora" / "ARQUITECTURA.md"
LEGACY_AUDIT = ROOT / "docs" / "architecture" / "FASE_1_AUDITORIA_Y_ARQUITECTURA.md"
LEGACY_TARGET = ROOT / "docs" / "architecture" / "ARQUITECTURA_OBJETIVO_CONSTRUCONTROL.md"
LEGACY_MODULES = ROOT / "docs" / "architecture" / "module_inventory.json"
FILE_INVENTORY = ROOT / "docs" / "architecture" / "file_inventory.json"
LEGACY_WORKSPACE = (
	ROOT / "erpnext" / "construcontrol" / "workspace" / "construcontrol" / "construcontrol.json"
)

errors: list[str] = []

for path in (
	NEXORA_ARCHITECTURE,
	LEGACY_AUDIT,
	LEGACY_TARGET,
	LEGACY_MODULES,
	FILE_INVENTORY,
	LEGACY_WORKSPACE,
):
	if not path.is_file():
		errors.append(f"Missing architecture source: {path.relative_to(ROOT)}")

if errors:
	print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
	raise SystemExit(1)

legacy_inventory = json.loads(LEGACY_MODULES.read_text(encoding="utf-8"))
file_inventory_manifest = json.loads(FILE_INVENTORY.read_text(encoding="utf-8"))
file_inventory = build_inventory()
workspace = json.loads(LEGACY_WORKSPACE.read_text(encoding="utf-8"))
nexora_text = NEXORA_ARCHITECTURE.read_text(encoding="utf-8")
legacy_audit_text = LEGACY_AUDIT.read_text(encoding="utf-8")
legacy_target_text = LEGACY_TARGET.read_text(encoding="utf-8")

if legacy_inventory.get("product") != "ConstruControl":
	errors.append("Legacy module inventory must remain explicitly identified as ConstruControl")
if legacy_inventory.get("source_of_truth", {}).get("branch") != "main":
	errors.append("Legacy architecture inventory must declare main as its production source of truth")
if file_inventory.get("product") != "NEXORA":
	errors.append("Canonical repository file inventory product must be NEXORA")
if file_inventory.get("legacy_product") != "ConstruControl":
	errors.append("Canonical repository inventory must identify ConstruControl as the legacy product")
if file_inventory_manifest != build_manifest(file_inventory):
	errors.append("File inventory manifest does not match the generated canonical inventory")
if file_inventory.get("tracked_files") != len(file_inventory.get("entries") or []):
	errors.append("File inventory count does not match its entries")

file_entries = file_inventory.get("entries") or []
inventory_paths = [entry.get("path") for entry in file_entries]
if len(inventory_paths) != len(set(inventory_paths)):
	errors.append("File inventory paths must be unique")

allowed_classifications = {
	"CORE",
	"SUPPORT",
	"CONFIGURATION",
	"TEST",
	"DOCUMENTATION",
	"MIGRATION",
	"INFRASTRUCTURE",
	"GENERATED",
	"THIRD_PARTY",
	"OBSOLETE",
}
if any(entry.get("classification") not in allowed_classifications for entry in file_entries):
	errors.append("Every repository file must have an allowed explicit classification")

required_product_fields = {
	"domain",
	"purpose",
	"consumers",
	"imports_hooks_routes",
	"data_access",
	"permissions",
	"side_effects",
	"related_tests",
	"decision",
}
product_ownerships = {
	"NEXORA",
	"ConstruControl legacy",
	"Shared repository platform",
}
for entry in file_entries:
	if entry.get("ownership") not in product_ownerships:
		continue
	missing_fields = sorted(field for field in required_product_fields if not entry.get(field))
	if missing_fields:
		errors.append(f"File inventory entry {entry.get('path')} is missing: {', '.join(missing_fields)}")

for phrase in (
	"PRODUCTO_VISIBLE: NEXORA",
	"REPOSITORIO_OFICIAL: Clopezgg/Gesti-n-de-Construcci-n-Residencial",
	"NO_MIGRACION_HISTORICA: true",
	"NO_SEGUNDO_REPOSITORIO: true",
	"NO_SEGUNDO_LEDGER_CANONICO: true",
	"NEXORA se implementa como aplicación Frappe separada dentro de `nexora_app/`",
	"ConstruControl permanece intacto como referencia heredada temporal",
):
	if phrase not in nexora_text:
		errors.append(f"NEXORA architecture is missing binding statement: {phrase}")

required_guardrails = {
	"No eliminar volúmenes Docker",
	"No ejecutar docker compose down -v",
	"No realizar cambios permanentes únicamente en AWS o Coolify",
	"No guardar secretos en GitHub",
	"Toda migración de esquema debe ser idempotente",
}
actual_guardrails = set(legacy_inventory.get("infrastructure_guardrails") or [])
missing_guardrails = sorted(required_guardrails - actual_guardrails)
if missing_guardrails:
	errors.append("Missing inherited infrastructure guardrails: " + ", ".join(missing_guardrails))

modules = legacy_inventory.get("modules") or []
if not isinstance(modules, list) or len(modules) < 17:
	errors.append("Legacy module inventory must retain the complete ConstruControl coexistence surface")

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
		errors.append("Legacy module without code")
		continue
	if code in seen_codes:
		errors.append(f"Duplicate legacy module code: {code}")
	seen_codes.add(code)
	if target:
		if target in seen_targets:
			errors.append(f"Duplicate legacy module target: {target}")
		seen_targets.add(target)
	if not isinstance(owner_phase, int) or owner_phase < 2 or owner_phase > 12:
		errors.append(f"Invalid legacy owner phase for {code}: {owner_phase}")
	if module.get("shell_required") is not True:
		errors.append(f"Legacy module is not covered by the unified shell contract: {code}")

missing_codes = sorted(required_codes - seen_codes)
if missing_codes:
	errors.append("Missing required legacy product modules: " + ", ".join(missing_codes))

workspace_targets = {
	f"{row.get('link_type')}:{row.get('link_to')}"
	for row in workspace.get("links", [])
	if row.get("link_type") in {"DocType", "Page"} and row.get("link_to")
}
registered_targets = set(seen_targets)
unregistered_workspace_targets = sorted(workspace_targets - registered_targets)
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
	errors.append(
		"Legacy workspace targets missing coexistence ownership: " + ", ".join(unregistered_workspace_targets)
	)

for phrase in (
	"ERPNext/Frappe permanece como motor interno",
	"No se dará una fase por completada con pruebas fallidas",
	"Datos productivos modificados: **ninguno**",
):
	if phrase not in legacy_audit_text:
		errors.append(f"Legacy audit is missing inherited safety statement: {phrase}")

for phrase in (
	"Contrato de navegación",
	"Contrato financiero",
	"Contrato de PWA",
	"Estrategia de evolución sin dañar producción",
):
	if phrase not in legacy_target_text:
		errors.append(f"Legacy target architecture is missing coexistence contract: {phrase}")

ownership_counts = file_inventory.get("ownership_counts") or {}
if ownership_counts.get("NEXORA", 0) <= 0:
	errors.append("Canonical inventory contains no NEXORA-owned files")
if ownership_counts.get("ConstruControl legacy", 0) <= 0:
	errors.append("Canonical inventory does not preserve the legacy ConstruControl boundary")

result = {
	"ok": not errors,
	"product": "NEXORA",
	"tracked_files": file_inventory.get("tracked_files"),
	"ownership_counts": ownership_counts,
	"legacy_modules": len(modules),
	"legacy_workspace_targets_reviewed": len(workspace_targets),
	"guardrails_present": not missing_guardrails,
	"errors": errors,
}
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if not errors else 1)
