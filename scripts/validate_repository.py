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

VALIDATION_ROOTS = (
    ROOT / "erpnext" / "construcontrol",
    ROOT / "scripts",
    ROOT / "deploy" / "coolify",
)

REQUIRED_FILES = (
    "README.md",
    ".env.example",
    "MANUAL_PASO_A_PASO.md",
    "Dockerfile",
    "docker-compose.yml",
    ".github/workflows/construcontrol-validation.yml",
    "docs/deployment/AWS_COOLIFY.md",
    "docs/migration/MAPA_CORRESPONDENCIA.md",
    "docs/migration/MIGRACION_Y_ROLLBACK.md",
    "erpnext/hooks.py",
    "erpnext/construcontrol/api.py",
    "erpnext/construcontrol/controllers.py",
    "erpnext/construcontrol/install.py",
    "erpnext/construcontrol/integration.py",
    "erpnext/construcontrol/migration/schema.py",
    "erpnext/construcontrol/migration/importer.py",
    "erpnext/construcontrol/migration/operational_importer.py",
    "erpnext/construcontrol/migration/backup_reader.py",
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
)

for base in VALIDATION_ROOTS:
    if not base.exists():
        errors.append(f"Missing validation root: {base.relative_to(ROOT)}")

for relative in REQUIRED_FILES:
    if not (ROOT / relative).exists():
        errors.append(f"Missing required file: {relative}")

# A second workflow previously duplicated the same checks and produced conflicting
# results. Production uses one authoritative workflow only.
duplicate_workflow = ROOT / ".github" / "workflows" / "construcontrol-integration.yml"
if duplicate_workflow.exists():
    errors.append("Duplicate CI workflow must not exist: .github/workflows/construcontrol-integration.yml")

if (ROOT / "render.yaml").exists():
    errors.append("render.yaml must not exist: Render is not the production architecture")

# Parse every ConstruControl JSON and Python source.
json_paths = [path for base in VALIDATION_ROOTS if base.exists() for path in base.rglob("*.json")]
python_paths = [path for base in VALIDATION_ROOTS if base.exists() for path in base.rglob("*.py")]
python_paths.append(ROOT / "erpnext" / "hooks.py")

for path in json_paths:
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"Invalid JSON {path.relative_to(ROOT)}: {exc}")

for path in python_paths:
    if not path.exists():
        continue
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except Exception as exc:
        errors.append(f"Invalid Python {path.relative_to(ROOT)}: {exc}")

modules_path = ROOT / "erpnext" / "modules.txt"
if not modules_path.exists() or "ConstruControl" not in modules_path.read_text(encoding="utf-8").splitlines():
    errors.append("ConstruControl is not registered in erpnext/modules.txt")

# Validate the active AWS EC2 + Coolify Compose topology.
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

unexpected_one_shot = {"configurator", "init-site"} & set(services)
if unexpected_one_shot:
    errors.append(
        "One-shot services must not be reintroduced; backend owns guarded initialization: "
        + ", ".join(sorted(unexpected_one_shot))
    )

volumes = compose.get("volumes") if isinstance(compose, dict) else None
if not isinstance(volumes, dict):
    errors.append("docker-compose.yml must define persistent volumes")
    volumes = {}
expected_volumes = {"mariadb-data", "redis-queue-data", "sites", "logs"}
missing_volumes = expected_volumes - set(volumes)
if missing_volumes:
    errors.append(f"docker-compose.yml is missing volumes: {', '.join(sorted(missing_volumes))}")

for service_name in ("mariadb", "redis-cache", "redis-queue"):
    service = services.get(service_name, {})
    if service.get("ports"):
        errors.append(f"{service_name} must remain private and must not publish host ports")

frontend = services.get("frontend", {})
if "8080" not in {str(value) for value in frontend.get("expose", [])}:
    errors.append("frontend must expose internal port 8080 for the Coolify proxy")
if frontend.get("ports"):
    errors.append("frontend must be routed by Coolify and must not publish a fixed host port")

for service_name in ("backend", "websocket", "queue-short", "queue-long", "scheduler", "frontend", "backup"):
    mounts = services.get(service_name, {}).get("volumes", []) or []
    if not any(str(mount).startswith("sites:") for mount in mounts):
        errors.append(f"{service_name} must mount the persistent sites volume")

backend_command = str(services.get("backend", {}).get("command") or "")
if "start-backend.sh" not in backend_command:
    errors.append("backend must start through deploy/coolify/start-backend.sh")

start_backend_path = ROOT / "deploy" / "coolify" / "start-backend.sh"
if start_backend_path.exists():
    start_backend = start_backend_path.read_text(encoding="utf-8")
    if "init-site.sh" not in start_backend:
        errors.append("start-backend.sh must execute init-site.sh before Gunicorn")

init_site_path = ROOT / "deploy" / "coolify" / "init-site.sh"
if init_site_path.exists():
    init_site = init_site_path.read_text(encoding="utf-8")
    required_guards = (
        "Existing ERPNext database detected",
        "bench --site \"$SITE_NAME\" migrate",
        "Refusing to overwrite it automatically",
    )
    for phrase in required_guards:
        if phrase not in init_site:
            errors.append(f"init-site.sh is missing safety guard: {phrase}")

backup_now_path = ROOT / "deploy" / "coolify" / "backup-now.sh"
if backup_now_path.exists():
    backup_now = backup_now_path.read_text(encoding="utf-8")
    for phrase in ("sites/${SITE_NAME}/private/backups", "sites/${SITE_NAME}/private/backup-archive", "backup --with-files"):
        if phrase not in backup_now:
            errors.append(f"backup-now.sh is missing persistent backup behavior: {phrase}")

# Documentation must describe the actual production architecture and reject old procedures.
documentation_checks = {
    "README.md": ("AWS EC2", "Coolify", "docker-compose.yml", "sites/<SITE_NAME>/private/backups"),
    "MANUAL_PASO_A_PASO.md": ("AWS EC2", "Security Group", "Coolify", "/docker-compose.yml", "ConstruControl Settings"),
    "docs/deployment/AWS_COOLIFY.md": ("AWS EC2", "linux/amd64", "frontend", "sites/<SITE_NAME>/private/backups"),
    ".env.example": ("AWS EC2", "BACKUP_RUN_ON_START=false", "SUPABASE_STORAGE_MODE=disabled"),
}
for relative, phrases in documentation_checks.items():
    path = ROOT / relative
    if not path.exists():
        continue
    text = path.read_text(encoding="utf-8")
    for phrase in phrases:
        if phrase not in text:
            errors.append(f"{relative} is missing production instruction: {phrase}")
    for index, character in enumerate(text):
        if ord(character) < 32 and character not in "\n\r\t":
            errors.append(f"{relative} contains a control character at offset {index}")
            break

readme = (ROOT / "README.md").read_text(encoding="utf-8") if (ROOT / "README.md").exists() else ""
if "Oracle Cloud Always Free" in readme or "VM.Standard.A1.Flex" in readme:
    errors.append("README.md still presents Oracle as the production architecture")
if "Blueprint de Render" in readme:
    errors.append("README.md still presents Render Blueprint as active")

workflow_path = ROOT / ".github" / "workflows" / "construcontrol-validation.yml"
if workflow_path.exists():
    workflow = workflow_path.read_text(encoding="utf-8")
    if "linux/amd64" not in workflow or "AWS EC2 x86_64" not in workflow:
        errors.append("The authoritative workflow must build the AWS EC2 linux/amd64 image")
    if "linux/arm64" in workflow or "Oracle Ampere" in workflow:
        errors.append("The authoritative workflow still contains the retired ARM64 topology")

# Shell scripts must use LF and a Bash shebang.
for path in (ROOT / "deploy" / "coolify").glob("*.sh") if (ROOT / "deploy" / "coolify").exists() else []:
    raw = path.read_bytes()
    if b"\r\n" in raw:
        errors.append(f"Deployment script uses CRLF instead of LF: {path.relative_to(ROOT)}")
    if not raw.startswith(b"#!/usr/bin/env bash"):
        errors.append(f"Deployment script lacks the expected bash shebang: {path.relative_to(ROOT)}")

# Search text files for secrets that must never be committed.
secret_patterns = (
    re.compile(r"sb_secret_[A-Za-z0-9_-]{12,}"),
    re.compile(r"service_role\s*[:=]\s*['\"][A-Za-z0-9._-]{20,}", re.I),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"postgres(?:ql)?://[^\s:]+:[^\s@]{8,}@", re.I),
)
for path in ROOT.rglob("*"):
    if not path.is_file() or ".git" in path.parts:
        continue
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".ico", ".mp3", ".zip", ".gz", ".pdf"}:
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
