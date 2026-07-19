#!/usr/bin/env python3
from __future__ import annotations

import ast
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / "erpnext" / "construcontrol" / "runtime"
CONTRACT_MODULE = ROOT / "erpnext" / "construcontrol" / "migration" / "runtime_contract.py"
OPERATIONAL_IMPORTER = ROOT / "erpnext" / "construcontrol" / "migration" / "operational_importer.py"
IMPORTER = ROOT / "erpnext" / "construcontrol" / "migration" / "importer.py"
API = ROOT / "erpnext" / "construcontrol" / "api.py"
INSTALL = ROOT / "erpnext" / "construcontrol" / "install.py"


def load_contract_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "construcontrol_runtime_contract",
        CONTRACT_MODULE,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar {CONTRACT_MODULE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def entity_doctypes() -> dict[str, str]:
    tree = ast.parse(OPERATIONAL_IMPORTER.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(
            isinstance(target, ast.Name) and target.id == "ENTITY_DOCTYPES"
            for target in targets
        ):
            continue
        value = ast.literal_eval(node.value)
        if isinstance(value, dict):
            return {
                str(source): str(target)
                for source, target in value.items()
                if source and target
            }
    raise RuntimeError("No se encontró ENTITY_DOCTYPES como diccionario literal")


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    required_files = (
        CONTRACT_MODULE,
        OPERATIONAL_IMPORTER,
        IMPORTER,
        API,
        INSTALL,
    )
    for path in required_files:
        if not path.is_file():
            errors.append(f"Falta archivo de contrato de datos: {path.relative_to(ROOT)}")

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
        return 1

    mapping = entity_doctypes()
    contract = load_contract_module()
    report = contract.validate_runtime_contract(
        RUNTIME_DIR,
        required_doctypes=set(mapping.values()),
    )
    errors.extend(report.get("errors") or [])
    warnings.extend(report.get("warnings") or [])

    importer_text = IMPORTER.read_text(encoding="utf-8")
    api_text = API.read_text(encoding="utf-8")
    install_text = INSTALL.read_text(encoding="utf-8")
    operational_text = OPERATIONAL_IMPORTER.read_text(encoding="utf-8")

    required_importer_controls = (
        "SELECT GET_LOCK(%s, %s)",
        "SELECT RELEASE_LOCK(%s)",
        "is_logically_deleted = 1",
        '"hard_deleted": 0',
        "in_construcontrol_migration",
        "_normalize_temporal_values",
    )
    for phrase in required_importer_controls:
        if phrase not in importer_text:
            errors.append(f"El importador no aplica el control obligatorio: {phrase}")

    if re.search(
        r"frappe\.delete_doc\(\s*[\"']CC User Access[\"']",
        importer_text,
    ):
        errors.append(
            "La consolidación de usuarios no puede borrar físicamente CC User Access"
        )

    for phrase in (
        "source_sha != validated_run.source_sha256",
        "_create_database_backup",
        "frappe.db.rollback()",
    ):
        if phrase not in api_text:
            errors.append(f"La API de migración perdió el control: {phrase}")

    for phrase in (
        "_validate_runtime_definitions",
        "validate_runtime_contract_or_raise",
        "before the first database mutation",
    ):
        if phrase not in install_text:
            errors.append(f"after_migrate no valida primero el contrato runtime: {phrase}")

    for phrase in (
        "mismatches",
        "La conciliación de cantidades falló",
        'clean["source_key"] = key',
    ):
        if phrase not in operational_text:
            errors.append(f"El importador operacional perdió el control: {phrase}")

    destructive_sql = re.compile(
        r"\b(?:DROP\s+TABLE|TRUNCATE\s+TABLE|DELETE\s+FROM)\b",
        re.IGNORECASE,
    )
    for path in (ROOT / "erpnext" / "construcontrol" / "migration").glob("*.py"):
        if destructive_sql.search(path.read_text(encoding="utf-8", errors="ignore")):
            errors.append(
                f"SQL destructivo no permitido en migración: {path.relative_to(ROOT)}"
            )

    result = {
        "ok": not errors,
        "contract_version": report.get("contract_version"),
        "contract_sha256": report.get("sha256"),
        "source_entities": len(mapping),
        "target_doctypes": len(set(mapping.values())),
        "runtime_doctypes": report.get("doctype_count"),
        "runtime_assets": report.get("asset_count"),
        "warnings": warnings,
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
