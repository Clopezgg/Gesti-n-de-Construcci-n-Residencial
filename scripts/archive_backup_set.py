#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
	digest = hashlib.sha256()
	with path.open("rb") as handle:
		while chunk := handle.read(1024 * 1024):
			digest.update(chunk)
	return digest.hexdigest()


def main() -> int:
	parser = argparse.ArgumentParser(
		description="Archive one freshly generated Bench backup set in a persistent volume."
	)
	parser.add_argument("--directory", required=True, type=Path)
	parser.add_argument("--destination", required=True, type=Path)
	parser.add_argument("--newer-than", required=True, type=float)
	parser.add_argument("--site", required=True)
	parser.add_argument("--retention-days", type=int, default=14)
	args = parser.parse_args()

	source = args.directory.expanduser().resolve()
	destination = args.destination.expanduser().resolve()
	if not source.is_dir():
		raise RuntimeError(f"Backup source directory does not exist: {source}")
	if args.retention_days < 1:
		raise RuntimeError("Retention days must be at least 1.")

	files = [
		path
		for path in sorted(source.iterdir())
		if path.is_file() and path.stat().st_mtime >= args.newer_than - 2
	]
	if not files:
		raise RuntimeError("Bench produced no new backup files for this run.")

	now = datetime.now(timezone.utc)
	timestamp = now.strftime("%Y%m%dT%H%M%SZ")
	target = destination / args.site / now.strftime("%Y/%m/%d") / timestamp
	target.mkdir(parents=True, exist_ok=False)

	manifest: dict[str, object] = {
		"format": "construcontrol-local-backup-v1",
		"site": args.site,
		"created_at_utc": now.isoformat(),
		"path": str(target),
		"files": [],
	}
	file_rows: list[dict[str, object]] = []
	for source_file in files:
		target_file = target / source_file.name
		shutil.copy2(source_file, target_file)
		file_rows.append(
			{
				"name": target_file.name,
				"bytes": target_file.stat().st_size,
				"sha256": sha256_file(target_file),
			}
		)
	manifest["files"] = file_rows

	manifest_path = target / "backup-manifest.json"
	manifest_path.write_text(
		json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
		encoding="utf-8",
	)

	cutoff = now - timedelta(days=args.retention_days)
	site_root = destination / args.site
	removed: list[str] = []
	if site_root.is_dir():
		for candidate in sorted(site_root.rglob("backup-manifest.json")):
			try:
				payload = json.loads(candidate.read_text(encoding="utf-8"))
				created = datetime.fromisoformat(str(payload["created_at_utc"]))
				if created.tzinfo is None:
					created = created.replace(tzinfo=timezone.utc)
			except Exception:
				continue
			if created < cutoff:
				backup_dir = candidate.parent
				shutil.rmtree(backup_dir)
				removed.append(str(backup_dir))

	result = {
		"manifest": str(manifest_path),
		"files": len(file_rows),
		"bytes": sum(int(row["bytes"]) for row in file_rows),
		"retention_days": args.retention_days,
		"removed_old_sets": removed,
	}
	print(json.dumps(result, ensure_ascii=False, indent=2))
	return 0


if __name__ == "__main__":
	try:
		raise SystemExit(main())
	except Exception as exc:
		print(f"Local backup archive failed: {exc}", file=sys.stderr)
		raise SystemExit(1)
