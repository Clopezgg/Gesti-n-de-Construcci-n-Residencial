#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "docs" / "architecture" / "file_inventory.json"
CLASSIFICATIONS = {
	"CORE",
	"SUPPORT",
	"CONFIGURATION",
	"TEST",
	"DOCUMENTATION",
	"MIGRATION",
	"INFRASTRUCTURE",
	"GENERATED",
	"THIRD_PARTY",
	"DUPLICATE",
	"OUT_OF_DOMAIN",
	"OBSOLETE",
	"DANGEROUS",
	"REMOVAL_CANDIDATE",
}

PRODUCT_PREFIXES = (
	"deploy/",
	"docs/architecture/",
	"docs/deployment/",
	"docs/historical/",
	"docs/migration/",
	"docs/reconstruction/",
	"erpnext/construcontrol/",
	"migration/",
	"scripts/",
)
PRODUCT_ROOT_FILES = {
	".dockerignore",
	".env.example",
	"AGENTS.md",
	"Dockerfile",
	"MANUAL_PASO_A_PASO.md",
	"README.md",
	"docker-compose.yml",
}


def _git(*args: str, check: bool = True) -> list[str]:
	completed = subprocess.run(
		["git", *args],
		cwd=ROOT,
		check=check,
		capture_output=True,
		text=True,
		encoding="utf-8",
	)
	return [line for line in completed.stdout.splitlines() if line]


def repository_paths() -> list[str]:
	paths = set(_git("ls-files", "--cached", "--others", "--exclude-standard"))
	paths.add("docs/architecture/file_inventory.json")
	return sorted(path.replace("\\", "/") for path in paths)


def product_change_paths() -> set[str]:
	paths = set(_git("diff", "--name-only", "origin/main...HEAD", check=False))
	paths.update(_git("diff", "--name-only", check=False))
	paths.update(_git("diff", "--cached", "--name-only", check=False))
	return {path.replace("\\", "/") for path in paths}


def is_product_file(path: str, changed_paths: set[str]) -> bool:
	return (
		path in PRODUCT_ROOT_FILES
		or path in changed_paths
		or path.startswith(PRODUCT_PREFIXES)
		or "construcontrol" in path.casefold()
	)


def domain_for(path: str) -> str:
	value = path.casefold()
	rules = (
		("US01", ("/users", "/access", "/profile", "/permissions")),
		("FI02", ("expense", "payable", "invoice", "payment")),
		("FI01", ("finance", "funding", "remittance", "financial_institution")),
		("CO01", ("contract", "change_order")),
		("PR01", ("construction", "project", "phase")),
		("MM02", ("procurement", "purchase", "quotation")),
		("MIGO", ("inventory", "stock_entry", "material_movement")),
		("MM01", ("material", "catalog")),
		("QC01", ("quality", "evidence", "progress", "incident", "safety")),
		("CL01", ("closing", "weekly")),
		("AU01", ("audit", "forensic")),
		("BI01", ("report", "executive", "dashboard", "notification")),
		("MIG", ("migration", "backup", "restore", "supabase")),
	)
	for domain, markers in rules:
		if any(marker in value for marker in markers):
			return domain
	return "PLATFORM"


def classification_for(path: str, *, product: bool) -> str:
	value = path.casefold()
	if not product:
		return "THIRD_PARTY"
	if value.startswith("docs/historical/") or value.endswith("upload_backup_set.py"):
		return "OBSOLETE"
	if "/tests/" in value or value.startswith("tests/") or Path(value).name.startswith("test_"):
		return "TEST"
	if (
		value == "docs/architecture/file_inventory.json"
		or "/runtime/definitions_" in value
		or value.endswith("module_inventory.json")
	):
		return "GENERATED"
	if value.endswith((".md", ".rst")) or value.startswith("docs/"):
		return "DOCUMENTATION"
	if value.startswith(("deploy/", ".github/workflows/")) or value in {"dockerfile", "docker-compose.yml"}:
		return "INFRASTRUCTURE"
	if value.startswith("migration/") or "/migration/" in value:
		return "MIGRATION"
	if value.endswith((".json", ".yaml", ".yml", ".toml")) or Path(value).name.startswith("."):
		return "CONFIGURATION"
	if value.startswith("erpnext/construcontrol/") or "construcontrol" in value:
		return "CORE"
	return "SUPPORT"


def surface_for(path: str) -> str:
	value = path.casefold()
	if value.startswith(".github/workflows/"):
		return "github_workflow"
	if "/page/" in value and value.endswith(".js"):
		return "frappe_page"
	if "/doctype/" in value:
		return "frappe_doctype"
	if value.endswith(".py"):
		return "python_module"
	if value.endswith(".js"):
		return "javascript_asset"
	if value.endswith(".sh"):
		return "shell_entrypoint"
	if value.endswith((".json", ".yaml", ".yml", ".toml")):
		return "declarative_configuration"
	return "repository_resource"


def references_for(path: str, surface: str) -> list[str]:
	if surface == "python_module":
		return [
			path.removesuffix(".py").replace("/", "."),
			"Frappe hooks or whitelisted method where declared",
		]
	if surface == "frappe_page":
		page_name = Path(path).parent.name.replace("_", "-")
		return [f"/app/{page_name}", "Frappe desk page registry"]
	if surface == "frappe_doctype":
		return ["Frappe DocType registry", "document events and server permissions"]
	if surface == "github_workflow":
		return ["GitHub pull_request/workflow_dispatch event graph"]
	if surface == "shell_entrypoint":
		return ["Docker Compose command or documented operator command"]
	return ["repository-relative reference or declared configuration consumer"]


def consumers_for(surface: str) -> list[str]:
	consumers = {
		"python_module": ["Frappe backend", "directed tests"],
		"frappe_page": ["ConstruControl Desk users", "browser certification"],
		"frappe_doctype": ["Frappe ORM", "ConstruControl services"],
		"javascript_asset": ["Frappe Desk client"],
		"github_workflow": ["GitHub Actions certification chain"],
		"shell_entrypoint": ["isolated Docker Compose runtime"],
		"declarative_configuration": ["Frappe, Docker or validation tooling"],
		"repository_resource": ["maintainers or validation tooling"],
	}
	return consumers[surface]


def tests_for(domain: str, paths: list[str]) -> list[str]:
	markers = {
		"US01": ("access", "users", "permissions"),
		"FI01": ("finance", "funding"),
		"FI02": ("expense", "fi02"),
		"PR01": ("construction", "project"),
		"CO01": ("contract", "construction"),
		"MM01": ("inventory", "catalog"),
		"MM02": ("inventory", "procurement"),
		"MIGO": ("inventory",),
		"QC01": ("quality",),
		"CL01": ("closing", "weekly"),
		"BI01": ("bi_", "executive", "reporting"),
		"AU01": ("audit",),
		"MIG": ("migration", "backup", "normalization", "runtime_contract"),
	}
	candidates = [path for path in paths if "/tests/test_" in path.casefold()]
	return [
		path for path in candidates if any(marker in path.casefold() for marker in markers.get(domain, ()))
	][:8]


def fallback_test_for(classification: str) -> str:
	if classification in {"INFRASTRUCTURE", "CONFIGURATION"}:
		return "erpnext/construcontrol/tests/test_infrastructure_contract_standalone.py"
	if classification == "DOCUMENTATION":
		return "erpnext/construcontrol/tests/test_documentation_check_standalone.py"
	if classification in {"MIGRATION", "OBSOLETE"}:
		return "erpnext/construcontrol/tests/test_migration_safety_standalone.py"
	return "erpnext/construcontrol/tests/test_ci_gate_contract_standalone.py"


def entry_for(path: str, all_paths: list[str], changed_paths: set[str]) -> dict[str, Any]:
	product = is_product_file(path, changed_paths)
	domain = domain_for(path) if product else "ERPNext"
	classification = classification_for(path, product=product)
	if classification not in CLASSIFICATIONS:
		raise ValueError(f"Unsupported classification for {path}: {classification}")
	surface = surface_for(path)
	if not product:
		return {
			"path": path,
			"classification": classification,
			"domain": domain,
			"ownership": "upstream ERPNext or repository dependency",
			"surface": surface,
			"decision": "retain_as_third_party_unless_product_diff_requires_review",
		}
	permissions = "project-scoped server authorization"
	if domain in {"US01", "MIG"}:
		permissions = "System Manager or ConstruControl management authorization"
	elif classification in {"DOCUMENTATION", "TEST", "INFRASTRUCTURE", "CONFIGURATION", "GENERATED"}:
		permissions = "not_runtime_callable"
	decision = "retain_and_test"
	if classification == "OBSOLETE":
		decision = "retain_only_as_explicit_tombstone_or_remove_after_reference_audit"
	ownership = "ConstruControl"
	if path.startswith("erpnext/") and not path.startswith("erpnext/construcontrol/"):
		ownership = "ConstruControl modification of upstream ERPNext"
	related_tests = tests_for(domain, all_paths) or [fallback_test_for(classification)]
	return {
		"path": path,
		"classification": classification,
		"domain": domain,
		"ownership": ownership,
		"surface": surface,
		"purpose": f"{domain} {classification.casefold()} responsibility",
		"consumers": consumers_for(surface),
		"imports_hooks_routes": references_for(path, surface),
		"data_access": "canonical server records and project scope"
		if classification == "CORE"
		else "none or test/configuration data",
		"permissions": permissions,
		"side_effects": "must be transaction-safe, auditable and rollback-aware"
		if classification in {"CORE", "MIGRATION"}
		else "none outside its declared surface",
		"related_tests": related_tests,
		"decision": decision,
	}


def build_inventory() -> dict[str, Any]:
	paths = repository_paths()
	changed_paths = product_change_paths()
	entries = [entry_for(path, paths, changed_paths) for path in paths]
	counts: dict[str, int] = {}
	for entry in entries:
		counts[entry["classification"]] = counts.get(entry["classification"], 0) + 1
	return {
		"schema_version": 1,
		"product": "ConstruControl",
		"tracked_files": len(entries),
		"classification_counts": dict(sorted(counts.items())),
		"entries": entries,
	}


def main() -> int:
	parser = argparse.ArgumentParser(
		description="Generate or verify the complete ConstruControl file inventory"
	)
	parser.add_argument("--check", action="store_true")
	args = parser.parse_args()
	expected = build_inventory()
	if args.check:
		if not TARGET.is_file():
			print(f"Missing file inventory: {TARGET.relative_to(ROOT)}")
			return 1
		actual = json.loads(TARGET.read_text(encoding="utf-8"))
		if actual != expected:
			print("File inventory is stale; run python scripts/generate_file_inventory.py")
			return 1
		print(f"File inventory verified: {expected['tracked_files']} repository files")
		return 0
	TARGET.parent.mkdir(parents=True, exist_ok=True)
	TARGET.write_text(json.dumps(expected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
	print(f"File inventory generated: {expected['tracked_files']} repository files")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
