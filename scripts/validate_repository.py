#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

try:
	import yaml
except ImportError as exc:  # pragma: no cover - explicit operator message
	raise SystemExit("PyYAML is required: python -m pip install PyYAML==6.0.2") from exc


ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []
validation_roots = (
	ROOT / "erpnext" / "construcontrol",
	ROOT / "scripts",
	ROOT / "deploy",
)

json_paths = [path for base in validation_roots for path in base.rglob("*.json")]
python_paths = [path for base in validation_roots for path in base.rglob("*.py")]
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
	"deploy/render/run-backup.sh",
	"deploy/render/Dockerfile.frontend",
	"deploy/render/nginx-main.conf",
	"render.yaml",
	"Dockerfile",
	".env.example",
	"MANUAL_PASO_A_PASO.md",
	"docs/migration/MAPA_CORRESPONDENCIA.md",
	"docs/migration/MIGRACION_Y_ROLLBACK.md",
	".github/workflows/construcontrol-validation.yml",
)
for relative in required:
	if not (ROOT / relative).exists():
		errors.append(f"Missing required file: {relative}")

modules = (ROOT / "erpnext" / "modules.txt").read_text(encoding="utf-8").splitlines()
if "ConstruControl" not in modules:
	errors.append("ConstruControl is not registered in erpnext/modules.txt")

# Validate the Render Blueprint beyond basic YAML parsing.
try:
	blueprint = yaml.safe_load((ROOT / "render.yaml").read_text(encoding="utf-8"))
except Exception as exc:
	errors.append(f"Invalid render.yaml: {exc}")
	blueprint = {}
services = blueprint.get("services") if isinstance(blueprint, dict) else None
if not isinstance(services, list):
	errors.append("render.yaml must contain a services list")
	services = []
service_by_name = {
	str(service.get("name")): service
	for service in services
	if isinstance(service, dict) and service.get("name")
}
expected_services = {
	"construcontrol-db",
	"construcontrol-redis-cache",
	"construcontrol-redis-queue",
	"construcontrol-backend",
	"construcontrol-websocket",
	"construcontrol-worker",
	"construcontrol-scheduler",
	"construcontrol-web",
	"construcontrol-backup",
}
missing_services = expected_services - set(service_by_name)
if missing_services:
	errors.append(f"render.yaml is missing services: {', '.join(sorted(missing_services))}")

backend = service_by_name.get("construcontrol-backend", {})
backend_env = {
	item.get("key"): item
	for item in backend.get("envVars", [])
	if isinstance(item, dict) and item.get("key")
}
for key in ("SUPABASE_URL", "SUPABASE_SERVER_KEY", "SUPABASE_STORAGE_BUCKET", "SUPABASE_MIGRATION_BUCKET", "SUPABASE_BACKUP_BUCKET"):
	if key not in backend_env:
		errors.append(f"Backend is missing Render variable {key}")
if "SUPABASE_SERVICE_ROLE_KEY" in backend_env:
	errors.append("render.yaml must use SUPABASE_SERVER_KEY, not the deprecated variable name")
if backend_env.get("SUPABASE_STORAGE_MODE", {}).get("value") != "enabled":
	errors.append("Production Supabase storage must be explicitly enabled in render.yaml")

frontend = service_by_name.get("construcontrol-web", {})
if frontend.get("dockerfilePath") != "./deploy/render/Dockerfile.frontend":
	errors.append("Frontend must use deploy/render/Dockerfile.frontend so nginx has the required runtime permissions")
backup = service_by_name.get("construcontrol-backup", {})
if backup.get("type") != "cron" or backup.get("dockerCommand") != "bash /home/frappe/frappe-bench/apps/erpnext/deploy/render/run-backup.sh":
	errors.append("Persistent remote backup cron is not configured correctly")

for service in services:
	if not isinstance(service, dict):
		continue
	for env_var in service.get("envVars", []) or []:
		if not isinstance(env_var, dict):
			continue
		reference = env_var.get("fromService")
		if isinstance(reference, dict) and reference.get("name") not in service_by_name:
			errors.append(
				f"{service.get('name')} references missing service {reference.get('name')} for {env_var.get('key')}"
			)

# Ensure runtime user separation remains deliberate.
def last_user(path: Path) -> str | None:
	users = [line.split(None, 1)[1].strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip().upper().startswith("USER ")]
	return users[-1] if users else None

if last_user(ROOT / "Dockerfile") != "frappe":
	errors.append("Application Dockerfile must end as USER frappe")
if last_user(ROOT / "deploy" / "render" / "Dockerfile.frontend") != "root":
	errors.append("Frontend Dockerfile must run the nginx master as root and drop workers to frappe in nginx-main.conf")
if "user frappe;" not in (ROOT / "deploy" / "render" / "nginx-main.conf").read_text(encoding="utf-8"):
	errors.append("nginx-main.conf must run nginx workers as frappe")

# The manual embeds the exact SQL so the operator never needs to hunt through the repository.
manual = (ROOT / "MANUAL_PASO_A_PASO.md").read_text(encoding="utf-8")
storage_sql = (ROOT / "migration" / "supabase" / "04_storage_bucket_and_rls.sql").read_text(encoding="utf-8").strip()
if storage_sql not in manual:
	errors.append("MANUAL_PASO_A_PASO.md is not synchronized with 04_storage_bucket_and_rls.sql")
for index, character in enumerate(manual):
	if ord(character) < 32 and character not in "\n\r\t":
		errors.append(f"Manual contains a control character at offset {index}")
		break

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
