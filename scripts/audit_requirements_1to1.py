#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

REQUIRED_MODULES = {
    "US01": ("erpnext/construcontrol/users.py", "erpnext/construcontrol/access.py"),
    "FI01": (
        "erpnext/construcontrol/finance.py",
        "erpnext/construcontrol/business_rules.py",
    ),
    "FI02": ("erpnext/construcontrol/expenses.py",),
    "PR01": ("erpnext/construcontrol/construction.py",),
    "CO01": ("erpnext/construcontrol/construction.py",),
    "MM01": ("erpnext/construcontrol/inventory.py",),
    "MM02": ("erpnext/construcontrol/inventory.py",),
    "MIGO": ("erpnext/construcontrol/inventory.py",),
    "QC01": ("erpnext/construcontrol/quality.py",),
    "CL01": ("erpnext/construcontrol/closing.py", "erpnext/construcontrol/weekly.py"),
    "BI01": (
        "erpnext/construcontrol/reporting.py",
        "erpnext/construcontrol/reporting_summary.py",
    ),
    "AU01": ("erpnext/construcontrol/audit.py",),
    "MIG": ("erpnext/construcontrol/migration", "deploy/coolify/restore-verify.sh"),
}

FORBIDDEN_ACTIVE_PATTERNS = (
    (re.compile(r"SUPABASE_BACKUP_BUCKET"), "Supabase backup bucket remains active"),
    (re.compile(r"upload_backup_set\.py"), "Production backup upload remains active"),
    (re.compile(r"continue-on-error", re.I), "CI hides failures"),
    (re.compile(r"\[skip ci\]|skip-ci", re.I), "CI bypass marker remains"),
)

REQUIRED_FILES = (
    "Dockerfile",
    "docker-compose.yml",
    "MANUAL_PASO_A_PASO.md",
    "deploy/coolify/backup-now.sh",
    "deploy/coolify/restore-verify.sh",
    "scripts/verify_backup_manifest.py",
    "scripts/audit_requirements_1to1.py",
    ".github/workflows/construcontrol-full-certification.yml",
    "erpnext/public/construcontrol/manifest.webmanifest",
    "erpnext/www/construcontrol-service-worker.js",
)


def check_file_exists(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    return {
        "id": f"file:{relative}",
        "passed": path.exists(),
        "detail": "present" if path.exists() else "missing",
    }


def active_text_files(root: Path) -> list[Path]:
    files = [
        root / "docker-compose.yml",
        root / "Dockerfile",
        root / ".env.example",
        root / "README.md",
        root / "MANUAL_PASO_A_PASO.md",
    ]
    files.extend((root / "deploy" / "coolify").glob("*.sh"))
    files.extend((root / ".github" / "workflows").glob("*.yml"))
    return [path for path in files if path.is_file()]


def run_audit(root: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    for relative in REQUIRED_FILES:
        checks.append(check_file_exists(root, relative))

    for module, paths in REQUIRED_MODULES.items():
        present = all((root / path).exists() for path in paths)
        checks.append(
            {
                "id": f"module:{module}",
                "passed": present,
                "detail": ", ".join(paths),
            }
        )

    compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
    services = {
        "mariadb",
        "redis-cache",
        "redis-queue",
        "backend",
        "websocket",
        "queue-short",
        "queue-long",
        "scheduler",
        "frontend",
        "backup",
    }
    for service in services:
        checks.append(
            {
                "id": f"service:{service}",
                "passed": re.search(rf"^  {re.escape(service)}:\s*$", compose, re.M)
                is not None,
                "detail": "declared in docker-compose.yml",
            }
        )
    checks.append(
        {
            "id": "architecture:linux-amd64",
            "passed": "platform: linux/amd64" in compose,
            "detail": "canonical deployment platform",
        }
    )
    checks.append(
        {
            "id": "architecture:no-public-db-ports",
            "passed": "3306:3306" not in compose and "6379:6379" not in compose,
            "detail": "MariaDB and Redis remain private",
        }
    )

    for path in active_text_files(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern, message in FORBIDDEN_ACTIVE_PATTERNS:
            checks.append(
                {
                    "id": f"forbidden:{path.relative_to(root)}:{pattern.pattern}",
                    "passed": pattern.search(text) is None,
                    "detail": message,
                }
            )

    manifest = json.loads(
        (
            root / "erpnext" / "public" / "construcontrol" / "manifest.webmanifest"
        ).read_text(encoding="utf-8")
    )
    checks.extend(
        [
            {
                "id": "pwa:start-url",
                "passed": manifest.get("start_url") == "/app/construcontrol-dashboard",
                "detail": str(manifest.get("start_url")),
            },
            {
                "id": "pwa:icons",
                "passed": {icon.get("sizes") for icon in manifest.get("icons", [])}
                >= {"192x192", "512x512"},
                "detail": "install icons",
            },
        ]
    )

    tracked_pages = list((root / "erpnext" / "construcontrol" / "page").glob("*/"))
    page_names = [path.name for path in tracked_pages]
    duplicates = sorted({name for name in page_names if page_names.count(name) > 1})
    checks.append(
        {
            "id": "canonical:page-duplicates",
            "passed": not duplicates,
            "detail": duplicates,
        }
    )

    failed = [check for check in checks if not check["passed"]]
    return {
        "schema": "construcontrol-audit-1to1-v1",
        "status": "passed" if not failed else "failed",
        "checks": len(checks),
        "passed": len(checks) - len(failed),
        "failed": len(failed),
        "failures": failed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independent ConstruControl 1:1 repository audit."
    )
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_audit(args.root.resolve())
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
