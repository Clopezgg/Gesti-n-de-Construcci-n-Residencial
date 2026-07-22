#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import pathlib
import re
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / "nexora_app"
PACKAGE = APP / "nexora"


def main() -> int:
    errors: list[str] = []
    required = [
        APP / "pyproject.toml",
        APP / "MANIFEST.in",
        PACKAGE / "__init__.py",
        PACKAGE / "hooks.py",
        PACKAGE / "modules.txt",
        PACKAGE / "patches.txt",
        PACKAGE / "install.py",
        PACKAGE / "permissions.py",
        PACKAGE / "fixtures/role.json",
        PACKAGE / "nexora/workspace/nexora/nexora.json",
    ]
    errors.extend(f"missing {path.relative_to(ROOT)}" for path in required if not path.is_file())
    if errors:
        return fail(errors)

    project = tomllib.loads((APP / "pyproject.toml").read_text(encoding="utf-8"))
    if project.get("project", {}).get("name") != "nexora":
        errors.append("project name must be nexora")
    dependencies = project.get("tool", {}).get("bench", {}).get("frappe-dependencies", {})
    if set(dependencies) != {"frappe", "erpnext"}:
        errors.append("Frappe dependencies must be exactly frappe and erpnext")

    hooks = (PACKAGE / "hooks.py").read_text(encoding="utf-8")
    ast.parse(hooks)
    for expected in ('app_name = "nexora"', 'app_title = "NEXORA"', 'required_apps = ["erpnext"]'):
        if expected not in hooks:
            errors.append(f"missing hook: {expected}")

    forbidden = []
    for path in APP.rglob("*"):
        if not path.is_file() or path.suffix not in {".py", ".json", ".js", ".css", ".md", ".toml"}:
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"(?:import|from)\s+erpnext\.construcontrol", text, re.IGNORECASE):
            forbidden.append(str(path.relative_to(ROOT)))
    if forbidden:
        errors.append(f"legacy imports found: {forbidden}")

    workspace = json.loads((PACKAGE / "nexora/workspace/nexora/nexora.json").read_text(encoding="utf-8"))
    if workspace.get("title") != "NEXORA" or workspace.get("module") != "NEXORA":
        errors.append("workspace identity is not NEXORA")
    serialized = json.dumps(workspace, ensure_ascii=False)
    if "ConstruControl" in serialized or "ERPNext" in serialized:
        errors.append("workspace leaks a legacy/internal product identity")

    roles = json.loads((PACKAGE / "fixtures/role.json").read_text(encoding="utf-8"))
    role_names = {row.get("name") for row in roles}
    workspace_roles = {row.get("role") for row in workspace.get("roles", [])}
    if role_names != workspace_roles or len(role_names) != 5:
        errors.append("role fixtures and workspace roles differ")

    if errors:
        return fail(errors)
    print("NEXORA app contract valid: separate package, five roles, clean workspace, no legacy import.")
    return 0


def fail(errors: list[str]) -> int:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
