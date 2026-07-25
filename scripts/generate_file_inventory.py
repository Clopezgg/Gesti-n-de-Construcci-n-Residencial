#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "docs" / "architecture" / "file_inventory.json"
REPOSITORY = "Clopezgg/Gesti-n-de-Construcci-n-Residencial"

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
    "OBSOLETE",
}

NEXORA_PREFIXES = (
    "nexora_app/",
    "docs/nexora/",
    "tools/nexora_monitor/",
)
LEGACY_PREFIXES = (
    "erpnext/construcontrol/",
    "docs/historical/",
    "docs/reconstruction/",
)
SHARED_PREFIXES = (
    ".github/workflows/",
    "deploy/",
    "docs/architecture/",
    "docs/deployment/",
    "docs/migration/",
    "migration/",
    "scripts/",
)
SHARED_ROOT_FILES = {
    ".dockerignore",
    ".env.example",
    ".eslintrc",
    ".gitignore",
    ".pre-commit-config.yaml",
    "AGENTS.md",
    "Dockerfile",
    "EXECUTION_STATE.md",
    "README.md",
    "docker-compose.yml",
    "opencode.json",
}


def _git(*args: str) -> list[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return [line for line in completed.stdout.splitlines() if line]


def repository_paths() -> list[str]:
    paths = set(_git("ls-files", "--cached"))
    paths.add("docs/architecture/file_inventory.json")
    return sorted(path.replace("\\", "/") for path in paths)


def ownership_for(path: str) -> str:
    value = path.casefold()
    if path.startswith(NEXORA_PREFIXES):
        return "NEXORA"
    if path.startswith(LEGACY_PREFIXES) or "construcontrol" in value:
        return "ConstruControl legacy"
    if path in SHARED_ROOT_FILES or path.startswith(SHARED_PREFIXES):
        return "Shared repository platform"
    return "Upstream ERPNext"


def domain_for(path: str, ownership: str) -> str:
    value = path.casefold()
    if ownership == "Upstream ERPNext":
        return "ERPNext"
    rules = (
        ("US01", ("user", "access", "profile", "permission", "role")),
        ("FI02", ("expense", "payable", "invoice", "payment", "budget")),
        ("FI01", ("finance", "fund", "remittance", "ledger", "operation")),
        ("CO01", ("contract", "change_order")),
        ("PR01", ("project", "phase", "progress")),
        ("MM02", ("purchase", "procurement", "quotation", "supplier")),
        ("MIGO", ("inventory", "stock", "warehouse", "receipt")),
        ("QC01", ("quality", "evidence", "incident", "safety")),
        ("CL01", ("close", "closing", "rollback")),
        ("AU01", ("audit", "governance", "forensic")),
        ("BI01", ("report", "dashboard", "notification", "search")),
        ("MIG", ("migration", "backup", "restore", "deploy")),
    )
    for domain, markers in rules:
        if any(marker in value for marker in markers):
            return domain
    return "PLATFORM"


def classification_for(path: str, ownership: str) -> str:
    value = path.casefold()
    name = Path(value).name
    if ownership == "Upstream ERPNext":
        return "THIRD_PARTY"
    if value.startswith("docs/historical/") or value.endswith("upload_backup_set.py"):
        return "OBSOLETE"
    if "/tests/" in value or value.startswith("tests/") or name.startswith("test_"):
        return "TEST"
    if value == "docs/architecture/file_inventory.json" or value.endswith("module_inventory.json"):
        return "GENERATED"
    if value.endswith((".md", ".rst")) or value.startswith("docs/"):
        return "DOCUMENTATION"
    if value.startswith(("deploy/", ".github/workflows/")) or value in {
        "dockerfile",
        "docker-compose.yml",
    }:
        return "INFRASTRUCTURE"
    if value.startswith("migration/") or "/migration/" in value:
        return "MIGRATION"
    if value.endswith((".json", ".yaml", ".yml", ".toml")) or name.startswith("."):
        return "CONFIGURATION"
    if value.startswith(("nexora_app/", "erpnext/construcontrol/")):
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
    if value.endswith((".ps1", ".sh")):
        return "operator_entrypoint"
    if value.endswith((".json", ".yaml", ".yml", ".toml")):
        return "declarative_configuration"
    return "repository_resource"


def references_for(path: str, surface: str) -> list[str]:
    if surface == "python_module":
        return [path.removesuffix(".py").replace("/", "."), "declared Frappe hook or test import"]
    if surface == "frappe_page":
        page_name = Path(path).parent.name.replace("_", "-")
        return [f"/app/{page_name}", "Frappe Page registry"]
    if surface == "frappe_doctype":
        return ["Frappe DocType registry", "document events and server permissions"]
    if surface == "github_workflow":
        return ["GitHub push and pull-request validation graph"]
    if surface == "operator_entrypoint":
        return ["documented local or CI operator command"]
    return ["repository-relative reference or declared configuration consumer"]


def consumers_for(surface: str, ownership: str) -> list[str]:
    product = "NEXORA" if ownership == "NEXORA" else ownership
    consumers = {
        "python_module": [f"{product} backend", "directed tests"],
        "frappe_page": [f"{product} Desk users", "browser certification"],
        "frappe_doctype": ["Frappe ORM", f"{product} services"],
        "javascript_asset": ["Frappe Desk client or local monitor"],
        "github_workflow": ["GitHub Actions certification chain"],
        "operator_entrypoint": ["local operator or isolated CI runtime"],
        "declarative_configuration": ["Frappe, CI or validation tooling"],
        "repository_resource": ["maintainers or validation tooling"],
    }
    return consumers[surface]


def related_tests_for(path: str, ownership: str, all_paths: list[str]) -> list[str]:
    value = path.casefold()
    candidates = [candidate for candidate in all_paths if "/tests/test_" in candidate.casefold()]
    markers = [
        part
        for part in Path(value).parts
        if len(part) > 3 and part not in {"nexora_app", "nexora"}
    ]
    related = [
        candidate
        for candidate in candidates
        if any(marker in candidate.casefold() for marker in markers[-4:])
    ]
    if related:
        return related[:8]
    if ownership == "NEXORA":
        return ["nexora_app/nexora/tests/test_app_contract.py"]
    if ownership == "ConstruControl legacy":
        return ["erpnext/construcontrol/tests/test_ci_gate_contract_standalone.py"]
    return ["scripts/validate_github_governance.py"]


def entry_for(path: str, all_paths: list[str]) -> dict[str, Any]:
    ownership = ownership_for(path)
    classification = classification_for(path, ownership)
    if classification not in CLASSIFICATIONS:
        raise ValueError(f"Unsupported classification for {path}: {classification}")
    surface = surface_for(path)
    if ownership == "Upstream ERPNext":
        return {
            "path": path,
            "classification": classification,
            "domain": "ERPNext",
            "ownership": ownership,
            "surface": surface,
            "decision": "retain_as_upstream_dependency_unless_a_product_diff_requires_review",
        }
    domain = domain_for(path, ownership)
    permissions = "not_runtime_callable"
    if classification in {"CORE", "MIGRATION"}:
        permissions = "server-side authorization scoped to the active NEXORA or legacy boundary"
    return {
        "path": path,
        "classification": classification,
        "domain": domain,
        "ownership": ownership,
        "surface": surface,
        "purpose": f"{domain} {classification.casefold()} responsibility",
        "consumers": consumers_for(surface, ownership),
        "imports_hooks_routes": references_for(path, surface),
        "data_access": "canonical NEXORA records, ERPNext records or isolated legacy records"
        if classification == "CORE"
        else "none or test/configuration data",
        "permissions": permissions,
        "side_effects": "must be transaction-safe, auditable and rollback-aware"
        if classification in {"CORE", "MIGRATION"}
        else "none outside its declared surface",
        "related_tests": related_tests_for(path, ownership, all_paths),
        "decision": "retain_and_test"
        if classification != "OBSOLETE"
        else "retain_only_as_explicit_history_or_remove_after_reference_audit",
    }


def build_inventory() -> dict[str, Any]:
    paths = repository_paths()
    entries = [entry_for(path, paths) for path in paths]
    classification_counts: dict[str, int] = {}
    ownership_counts: dict[str, int] = {}
    for entry in entries:
        classification = entry["classification"]
        ownership = entry["ownership"]
        classification_counts[classification] = classification_counts.get(classification, 0) + 1
        ownership_counts[ownership] = ownership_counts.get(ownership, 0) + 1
    return {
        "schema_version": 2,
        "product": "NEXORA",
        "legacy_product": "ConstruControl",
        "repository": REPOSITORY,
        "tracked_files": len(entries),
        "classification_counts": dict(sorted(classification_counts.items())),
        "ownership_counts": dict(sorted(ownership_counts.items())),
        "entries": entries,
    }


def canonical_inventory_sha256(inventory: dict[str, Any]) -> str:
    payload = json.dumps(
        inventory,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_manifest(inventory: dict[str, Any] | None = None) -> dict[str, Any]:
    inventory = inventory or build_inventory()
    return {
        "schema_version": 3,
        "format": "deterministic-inventory-manifest",
        "product": inventory["product"],
        "legacy_product": inventory["legacy_product"],
        "repository": inventory["repository"],
        "tracked_files": inventory["tracked_files"],
        "classification_counts": inventory["classification_counts"],
        "ownership_counts": inventory["ownership_counts"],
        "metadata_source": "scripts/generate_file_inventory.py",
        "canonical_inventory_sha256": canonical_inventory_sha256(inventory),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate or verify the canonical NEXORA repository inventory"
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    manifest = build_manifest()
    if args.check:
        if not TARGET.is_file():
            print(f"Missing file inventory manifest: {TARGET.relative_to(ROOT)}")
            return 1
        actual = json.loads(TARGET.read_text(encoding="utf-8"))
        if actual != manifest:
            print("File inventory manifest is stale; run python scripts/generate_file_inventory.py")
            return 1
        print(
            f"NEXORA file inventory verified: {manifest['tracked_files']} repository files, "
            f"sha256={manifest['canonical_inventory_sha256']}"
        )
        return 0
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"NEXORA file inventory generated: {manifest['tracked_files']} repository files, "
        f"sha256={manifest['canonical_inventory_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
