#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required: python -m pip install PyYAML==6.0.2") from exc

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []
validation_roots = (
    ROOT / "erpnext" / "construcontrol",
    ROOT / "scripts",
    ROOT / "deploy" / "coolify",
)

for base in validation_roots:
    if not base.exists():
        errors.append(f"Missing validation root: {base.relative_to(ROOT)}")

json_paths = [path for base in validation_roots if base.exists() for path in base.rglob("*.json")]
python_paths = [path for base in validation_roots if base.exists() for path in base.rglob("*.py")]
python_paths.extend((ROOT / "erpnext" / "hooks.py",))

for path in json_paths:
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"Invalid JSON {path.relative_to(ROOT)}: {exc}")

for path in python_paths:
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except Exception as exc:
        errors.append(f"Invalid Python {path.relative_to(ROOT)}: {exc}")

required = (
    "erpnext/construcontrol/migration/schema.py",
    "erpnext/construcontrol/migration/importer.py",
    "erpnext/construcontrol/migration/remote_importer.py",
    "erpnext/construcontrol/storage/supabase.py",
    "erpnext/construcontrol/doctype/construcontrol_legacy_record/construcontrol_legacy_record.json",
    "migration/supabase/01_preflight.sql",
    "migration/supabase/04_storage_bucket_and_rls.sql",
    "scripts/create_migration_bundle.py",
    "scripts/supabase_storage_transfer.py",
    "scripts/upload_backup_set.py",
    "scripts/archive_backup_set.py",
    "scripts/verify_backup_manifest.py",
    "deploy/coolify/configure-site.sh",
    "deploy/coolify/init-site.sh",
    "deploy/coolify/start-backend.sh",
    "deploy/coolify/start-websocket.sh",
    "deploy/coolify/start-worker.sh",
    "deploy/coolify/start-scheduler.sh",
    "deploy/coolify/backup-now.sh",
    "deploy/coolify/backup-loop.sh",
    "docker-compose.yml",
    "Dockerfile",
    ".env.example",
    "MANUAL_PASO_A_PASO.md",
    "docs/deployment/ORACLE_COOLIFY.md",
    "docs/migration/MAPA_CORRESPONDENCIA.md",
    "docs/migration/MIGRACION_Y_ROLLBACK.md",
    ".github/workflows/construcontrol-validation.yml",
)
for relative in required:
    if not (ROOT / relative).exists():
        errors.append(f"Missing required file: {relative}")

if (ROOT / "render.yaml").exists():
    errors.append("render.yaml must not exist: the paid Render Blueprint has been retired")

modules_path = ROOT / "erpnext" / "modules.txt"
if modules_path.exists():
    modules = modules_path.read_text(encoding="utf-8").splitlines()
    if "ConstruControl" not in modules:
        errors.append("ConstruControl is not registered in erpnext/modules.txt")

compose_path = ROOT / "docker-compose.yml"
try:
    compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
except Exception as exc:
    errors.append(f"Invalid docker-compose.yml: {exc}")
    compose = {}

services = compose.get("services") if isinstance(compose, dict) else None
if not isinstance(services, dict):
    errors.append("docker-compose.yml must contain a services mapping")
    services = {}

expected_services = {
    "mariadb",
    "redis-cache",
    "redis-queue",
    "configurator",
    "init-site",
    "backend",
    "websocket",
    "queue-short",
    "queue-long",
    "scheduler",
    "frontend",
    "backup",
}
missing_services = expected_services - set(services)
if missing_services:
    errors.append(f"docker-compose.yml is missing services: {', '.join(sorted(missing_services))}")

expected_volumes = {"mariadb-data", "redis-queue-data", "sites", "logs", "backups"}
volumes = compose.get("volumes") if isinstance(compose, dict) else None
if not isinstance(volumes, dict):
    errors.append("docker-compose.yml must define persistent volumes")
    volumes = {}
missing_volumes = expected_volumes - set(volumes)
if missing_volumes:
    errors.append(f"docker-compose.yml is missing volumes: {', '.join(sorted(missing_volumes))}")

for service_name in ("mariadb", "redis-cache", "redis-queue"):
    service = services.get(service_name, {})
    if "ports" in service:
        errors.append(f"{service_name} must remain private and must not publish host ports")

frontend = services.get("frontend", {})
if "8080" not in {str(value) for value in frontend.get("expose", [])}:
    errors.append("frontend must expose internal port 8080 for the Coolify proxy")

for service_name in ("backend", "websocket", "queue-short", "queue-long", "scheduler", "frontend", "backup"):
    mounts = services.get(service_name, {}).get("volumes", []) or []
    if not any(str(mount).startswith("sites:") for mount in mounts):
        errors.append(f"{service_name} must mount the persistent sites volume")

for service_name in ("backend", "backup"):
    mounts = services.get(service_name, {}).get("volumes", []) or []
    if not any(str(mount).startswith("backups:") for mount in mounts):
        errors.append(f"{service_name} must mount the persistent backups volume")

if "platform: linux/amd64" in compose_path.read_text(encoding="utf-8"):
    errors.append("docker-compose.yml must not force amd64; Oracle Always Free Ampere uses ARM64")

manual_path = ROOT / "MANUAL_PASO_A_PASO.md"
if manual_path.exists():
    manual = manual_path.read_text(encoding="utf-8")
    required_manual_phrases = (
        "Oracle Cloud",
        "VM.Standard.A1.Flex",
        "Coolify",
        "Docker Compose Location",
        "/docker-compose.yml",
        "SUPABASE_STORAGE_MODE=disabled",
        "docker compose down -v",
        "backup-manifest.json",
        "ConstruControl Settings",
    )
    for phrase in required_manual_phrases:
        if phrase not in manual:
            errors.append(f"Manual is missing required instruction: {phrase}")
    for index, character in enumerate(manual):
        if ord(character) < 32 and character not in "\n\r\t":
            errors.append(f"Manual contains a control character at offset {index}")
            break

readme_path = ROOT / "README.md"
if readme_path.exists():
    readme = readme_path.read_text(encoding="utf-8")
    if "docker-compose.yml" not in readme or "Oracle Cloud" not in readme or "Coolify" not in readme:
        errors.append("README.md does not describe the active Oracle Cloud + Coolify deployment")
    if "Blueprint de Render" in readme:
        errors.append("README.md still presents the retired paid Render Blueprint as active")

# Ensure all deployment scripts are shell-parseable and use Unix line endings.
for path in (ROOT / "deploy" / "coolify").glob("*.sh") if (ROOT / "deploy" / "coolify").exists() else []:
    raw = path.read_bytes()
    if b"\r\n" in raw:
        errors.append(f"Deployment script uses CRLF instead of LF: {path.relative_to(ROOT)}")
    if not raw.startswith(b"#!/usr/bin/env bash"):
        errors.append(f"Deployment script lacks the expected bash shebang: {path.relative_to(ROOT)}")

secret_patterns = (
    re.compile(r"sb_secret_[A-Za-z0-9_-]{12,}"),
    re.compile(r"service_role\s*[:=]\s*['\"][A-Za-z0-9._-]{20,}", re.I),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
for path in ROOT.rglob("*"):
    if not path.is_file() or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".ico", ".mp3"}:
        continue
    if path.stat().st_size > 2_000_000:
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    if any(pattern.search(text) for pattern in secret_patterns):
        errors.append(f"Possible committed secret in {path.relative_to(ROOT)}")

print(f"Repository validation: {len(errors)} error(s)", flush=True)
for error in errors:
    print(f"- {error}")
raise SystemExit(1 if errors else 0)
