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
PERMANENT_WORKFLOWS = {
	ROOT / ".github/workflows/nexora-app.yml",
	ROOT / ".github/workflows/nexora-financial.yml",
	ROOT / ".github/workflows/nexora-governance.yml",
}


def _module_candidates(module: str) -> tuple[pathlib.Path, pathlib.Path]:
	base = APP.joinpath(*module.split("."))
	return base.with_suffix(".py"), base / "__init__.py"


def _module_exists(module: str) -> bool:
	return any(candidate.is_file() for candidate in _module_candidates(module))


def _module_file(module: str) -> pathlib.Path | None:
	for candidate in _module_candidates(module):
		if candidate.is_file():
			return candidate
	return None


def _relative_module(path: pathlib.Path, node: ast.ImportFrom) -> str:
	package = list(path.relative_to(APP).with_suffix("").parts)
	package.pop()
	if node.level:
		keep = max(len(package) - (node.level - 1), 0)
		package = package[:keep]
	if node.module:
		package.extend(node.module.split("."))
	return ".".join(package)


def _local_import_errors(path: pathlib.Path) -> list[str]:
	errors: list[str] = []
	try:
		tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
	except SyntaxError as exc:
		return [f"invalid Python syntax in {path.relative_to(ROOT)}: {exc}"]
	for node in ast.walk(tree):
		modules: list[str] = []
		if isinstance(node, ast.Import):
			modules.extend(alias.name for alias in node.names)
		elif isinstance(node, ast.ImportFrom):
			modules.append(_relative_module(path, node) if node.level else str(node.module or ""))
		for module in modules:
			if module == "nexora" or module.startswith("nexora."):
				if not _module_exists(module):
					errors.append(
						f"missing local import {module!r} referenced by {path.relative_to(ROOT)}:{node.lineno}"
					)
	return errors


def _dotted_target_exists(target: str, seen: set[str] | None = None) -> bool:
	if "." not in target:
		return False
	seen = seen or set()
	if target in seen:
		return False
	seen.add(target)
	module, attribute = target.rsplit(".", 1)
	path = _module_file(module)
	if not path:
		return False
	try:
		tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
	except SyntaxError:
		return False
	for node in tree.body:
		if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) and node.name == attribute:
			return True
		if isinstance(node, ast.Assign | ast.AnnAssign):
			targets = node.targets if isinstance(node, ast.Assign) else [node.target]
			if any(isinstance(item, ast.Name) and item.id == attribute for item in targets):
				return True
		if isinstance(node, ast.ImportFrom):
			for alias in node.names:
				if (alias.asname or alias.name) != attribute:
					continue
				imported_module = _relative_module(path, node) if node.level else str(node.module or "")
				return _dotted_target_exists(f"{imported_module}.{alias.name}", seen)
		if isinstance(node, ast.Import):
			for alias in node.names:
				if (alias.asname or alias.name.split(".", 1)[0]) == attribute:
					return _module_exists(alias.name)
	return False


def _hook_targets(hooks_path: pathlib.Path) -> set[str]:
	tree = ast.parse(hooks_path.read_text(encoding="utf-8"), filename=str(hooks_path))
	targets: set[str] = set()
	for node in tree.body:
		if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
			continue
		if not isinstance(node.value.value, str):
			continue
		names = {target.id for target in node.targets if isinstance(target, ast.Name)}
		if names.intersection({"after_install", "after_migrate", "before_uninstall", "after_uninstall"}):
			targets.add(node.value.value)
	return targets


def _workflow_errors() -> list[str]:
	errors: list[str] = []
	workflow_dir = ROOT / ".github/workflows"
	actual = set(workflow_dir.glob("nexora-*.yml")) | set(workflow_dir.glob("nexora-*.yaml"))
	unexpected = actual - PERMANENT_WORKFLOWS
	missing = PERMANENT_WORKFLOWS - actual
	if unexpected:
		errors.append(
			"temporary or unapproved NEXORA workflows found: "
			+ ", ".join(str(path.relative_to(ROOT)) for path in sorted(unexpected))
		)
	if missing:
		errors.append(
			"missing permanent NEXORA workflows: "
			+ ", ".join(str(path.relative_to(ROOT)) for path in sorted(missing))
		)
	for path in sorted(actual):
		text = path.read_text(encoding="utf-8")
		if re.search(r"\bgit\s+(?:add|commit|push)\b", text):
			errors.append(f"workflow mutates repository history: {path.relative_to(ROOT)}")
		if re.search(r"contents\s*:\s*write", text):
			errors.append(f"workflow has write permission: {path.relative_to(ROOT)}")
		if any(
			token in text
			for token in ("block3-transport", "NEXORA CI Publisher", "base64 --decode", "base64 -d")
		):
			errors.append(f"temporary transport/publication mechanism found: {path.relative_to(ROOT)}")
	transport = ROOT / ".nexora"
	if transport.exists() and any(transport.rglob("*")):
		errors.append("temporary .nexora transport directory must not exist")
	return errors


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
		PACKAGE / "nexora/page/nexora_finance/nexora_finance.js",
		PACKAGE / "nexora/doctype/__init__.py",
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

	hooks_path = PACKAGE / "hooks.py"
	hooks = hooks_path.read_text(encoding="utf-8")
	ast.parse(hooks)
	for expected in ('app_name = "nexora"', 'app_title = "NEXORA"', 'required_apps = ["erpnext"]'):
		if expected not in hooks:
			errors.append(f"missing hook: {expected}")
	for target in sorted(_hook_targets(hooks_path)):
		if not _dotted_target_exists(target):
			errors.append(f"hook target does not exist: {target}")
	if "nexora.permissions.can_access_nexora" not in hooks:
		errors.append("apps screen permission hook is missing")
	elif not _dotted_target_exists("nexora.permissions.can_access_nexora"):
		errors.append("apps screen permission target does not exist")

	for path in sorted(APP.rglob("*.py")):
		errors.extend(_local_import_errors(path))

	doctype_root = PACKAGE / "nexora/doctype"
	for definition in sorted(doctype_root.glob("*/*.json")):
		payload = json.loads(definition.read_text(encoding="utf-8"))
		if payload.get("doctype") != "DocType":
			continue
		if payload.get("module") != "NEXORA":
			errors.append(f"DocType module must be NEXORA: {definition.relative_to(ROOT)}")
		controller = definition.with_suffix(".py")
		if not controller.is_file():
			errors.append(f"DocType controller is missing: {controller.relative_to(ROOT)}")

	forbidden = []
	for path in APP.rglob("*"):
		if not path.is_file() or path.suffix not in {".py", ".json", ".js", ".css", ".md", ".toml"}:
			continue
		text = path.read_text(encoding="utf-8")
		if re.search(r"(?:import|from)\s+erpnext\.construcontrol", text, re.IGNORECASE):
			forbidden.append(str(path.relative_to(ROOT)))
	if forbidden:
		errors.append(f"legacy imports found: {forbidden}")

	page = PACKAGE / "nexora/page/nexora_finance/nexora_finance.js"
	service_targets = set(
		re.findall(r'["\'](nexora(?:\.[A-Za-z_][A-Za-z0-9_]*){2,})["\']', page.read_text(encoding="utf-8"))
	)
	for target in sorted(service_targets):
		if target.startswith("nexora.financial.") and not _dotted_target_exists(target):
			errors.append(f"UI service target does not exist: {target}")

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

	errors.extend(_workflow_errors())
	if errors:
		return fail(errors)
	print(
		"NEXORA app contract valid: imports, hooks, UI services, three read-only workflows, five roles and clean identity."
	)
	return 0


def fail(errors: list[str]) -> int:
	for error in errors:
		print(f"ERROR: {error}", file=sys.stderr)
	return 1


if __name__ == "__main__":
	raise SystemExit(main())
