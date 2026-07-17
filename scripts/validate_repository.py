#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
from pathlib import Path


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
	"erpnext/construcontrol/doctype/construcontrol_legacy_record/construcontrol_legacy_record.json",
	"migration/supabase/01_preflight.sql",
	"migration/supabase/04_storage_bucket_and_rls.sql",
	"render.yaml",
	"Dockerfile",
	".env.example",
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
