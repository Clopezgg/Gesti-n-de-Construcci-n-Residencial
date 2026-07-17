#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from supabase_storage_transfer import upload_file


def sha256_file(path: Path) -> str:
	digest = hashlib.sha256()
	with path.open("rb") as handle:
		while chunk := handle.read(1024 * 1024):
			digest.update(chunk)
	return digest.hexdigest()


def main() -> int:
	parser = argparse.ArgumentParser(description="Upload one freshly generated Bench backup set to Supabase Storage.")
	parser.add_argument("--directory", required=True, type=Path)
	parser.add_argument("--newer-than", required=True, type=float, help="Unix timestamp used to select this run's files")
	parser.add_argument("--bucket", default=os.environ.get("SUPABASE_BACKUP_BUCKET", "construcontrol-backups"))
	parser.add_argument("--site", default=os.environ.get("SITE_NAME", "construcontrol"))
	parser.add_argument("--delete-local", action="store_true")
	args = parser.parse_args()

	directory = args.directory.expanduser().resolve()
	if not directory.is_dir():
		raise RuntimeError(f"Backup directory does not exist: {directory}")
	files = [
		path
		for path in sorted(directory.iterdir())
		if path.is_file() and path.stat().st_mtime >= args.newer_than - 2
	]
	if not files:
		raise RuntimeError("Bench produced no new backup files for this run.")

	timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
	prefix = f"{args.site}/{datetime.now(timezone.utc):%Y/%m/%d}/{timestamp}"
	manifest = {
		"format": "construcontrol-bench-backup-v1",
		"site": args.site,
		"created_at_utc": datetime.now(timezone.utc).isoformat(),
		"bucket": args.bucket,
		"prefix": prefix,
		"files": [],
	}
	for path in files:
		object_key = f"{prefix}/{path.name}"
		result = upload_file(path, args.bucket, object_key)
		manifest["files"].append(
			{
				"name": path.name,
				"object_key": object_key,
				"bytes": path.stat().st_size,
				"sha256": sha256_file(path),
				"upload_http_status": result["http_status"],
			}
		)

	with tempfile.TemporaryDirectory(prefix="construcontrol-backup-manifest-") as temporary:
		manifest_path = Path(temporary) / "backup-manifest.json"
		manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
		manifest_key = f"{prefix}/backup-manifest.json"
		upload_file(manifest_path, args.bucket, manifest_key, "application/json")
	manifest["manifest_object_key"] = manifest_key

	if args.delete_local:
		for path in files:
			path.unlink(missing_ok=True)
	print(json.dumps(manifest, ensure_ascii=False, indent=2))
	return 0


if __name__ == "__main__":
	try:
		raise SystemExit(main())
	except Exception as exc:
		print(f"Backup upload failed: {exc}", file=sys.stderr)
		raise SystemExit(1)
