#!/usr/bin/env python3
from __future__ import annotations

import json
import py_compile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
cc = root / "erpnext" / "construcontrol"
errors: list[str] = []

for path in cc.rglob("*.json"):
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"{path}: {exc}")
for path in cc.rglob("*.py"):
    if "__pycache__" not in path.parts:
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            errors.append(f"{path}: {exc}")

definitions = []
for path in sorted((cc / "runtime").glob("definitions_*.json")):
    definitions.extend(json.loads(path.read_text(encoding="utf-8")))
names = {row.get("name") for row in definitions}
required = {"CC Funding Source", "CC Expense Control", "CC Labor Contract", "CC Construction Phase", "CC Material Ledger", "CC Inventory Movement", "CC Evidence"}
missing = sorted(required - names)
if missing:
    errors.append("Missing required runtime DocTypes: " + ", ".join(missing))
assets = json.loads((cc / "runtime" / "assets.json").read_text(encoding="utf-8"))
if len(assets.get("pages", [])) < 2 or len(assets.get("reports", [])) < 3 or len(assets.get("print_formats", [])) < 3:
    errors.append("Runtime pages, reports or print formats are incomplete")
workspace = json.loads((cc / "workspace" / "construcontrol" / "construcontrol.json").read_text(encoding="utf-8"))
labels = {row.get("label") for row in workspace.get("links", [])}
for label in ("FI01 · Ingresos, remesas y aportes", "FI02 · Gastos y facturas", "CO01 · Contratos", "Migración segura"):
    if label not in labels:
        errors.append("Missing workspace link: " + label)
report = {"ok": not errors, "functional_doctypes": len(definitions), "required_present": not missing, "errors": errors, "images_imported_policy": 0}
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if not errors else 1)
