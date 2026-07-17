#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def require_env(name: str) -> str:
	value = os.environ.get(name, "").strip()
	if not value:
		raise RuntimeError(f"Missing required environment variable: {name}")
	return value


def request_json(url: str, key: str) -> Any:
	request = urllib.request.Request(
		url,
		headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"},
	)
	with urllib.request.urlopen(request, timeout=60) as response:
		return json.loads(response.read().decode("utf-8"))


def download(url: str, key: str) -> bytes:
	request = urllib.request.Request(url, headers={"apikey": key, "Authorization": f"Bearer {key}"})
	with urllib.request.urlopen(request, timeout=120) as response:
		return response.read()


def evidence_objects(value: Any) -> list[Mapping[str, Any]]:
	result: list[Mapping[str, Any]] = []
	if isinstance(value, list):
		for item in value:
			result.extend(evidence_objects(item))
	elif isinstance(value, Mapping):
		if value.get("storagePath"):
			result.append(value)
		for item in value.values():
			result.extend(evidence_objects(item))
	return result


def safe_relative_path(bucket: str, object_path: str) -> Path:
	parts = [part for part in object_path.replace("\\", "/").split("/") if part not in {"", ".", ".."}]
	return Path("evidence") / bucket / Path(*parts)


def main() -> int:
	parser = argparse.ArgumentParser(description="Export ConstruControl snapshots and referenced Supabase Storage objects.")
	parser.add_argument("output", type=Path, help="Empty or new output directory")
	parser.add_argument("--project-id", help="Override SUPABASE_PROJECT_ID")
	parser.add_argument("--skip-files", action="store_true", help="Export snapshots without downloading Storage objects")
	args = parser.parse_args()
	url = require_env("SUPABASE_URL").rstrip("/")
	key = require_env("SUPABASE_SERVICE_ROLE_KEY")
	project_id = (args.project_id or os.environ.get("SUPABASE_PROJECT_ID", "")).strip()

	query = "select=project_id,data,updated_at&order=project_id.asc"
	if project_id:
		query += "&project_id=eq." + urllib.parse.quote(project_id, safe="")
	rows = request_json(f"{url}/rest/v1/construction_projects?{query}", key)
	if not isinstance(rows, list) or not rows:
		raise RuntimeError("Supabase returned no construction_projects rows for the requested scope.")

	args.output.mkdir(parents=True, exist_ok=True)
	snapshot_path = args.output / "construcontrol-supabase-export.json"
	snapshot_path.write_text(json.dumps({"rows": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
	manifest: list[dict[str, Any]] = []
	seen: set[tuple[str, str]] = set()
	if not args.skip_files:
		for row in rows:
			for item in evidence_objects(row.get("data")):
				bucket = str(item.get("storageBucket") or "construction-evidence")
				object_path = str(item.get("storagePath"))
				identity = (bucket, object_path)
				if identity in seen:
					continue
				seen.add(identity)
				relative = safe_relative_path(bucket, object_path)
				target = args.output / relative
				encoded = urllib.parse.quote(object_path, safe="/")
				try:
					content = download(f"{url}/storage/v1/object/authenticated/{urllib.parse.quote(bucket)}/{encoded}", key)
					target.parent.mkdir(parents=True, exist_ok=True)
					target.write_bytes(content)
					manifest.append(
						{
							"bucket": bucket,
							"path": object_path,
							"exported_path": relative.as_posix(),
							"bytes": len(content),
							"sha256": hashlib.sha256(content).hexdigest(),
							"status": "downloaded",
						}
					)
				except urllib.error.HTTPError as exc:
					manifest.append(
						{"bucket": bucket, "path": object_path, "status": "failed", "http_status": exc.code}
					)
	manifest_path = args.output / "storage-manifest.json"
	manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
	failed = sum(1 for item in manifest if item["status"] == "failed")
	print(json.dumps({"projects": len(rows), "files": len(manifest), "failed_files": failed}, indent=2))
	return 3 if failed else 0


if __name__ == "__main__":
	try:
		raise SystemExit(main())
	except Exception as exc:
		print(f"Export failed: {exc}", file=sys.stderr)
		raise SystemExit(1)
