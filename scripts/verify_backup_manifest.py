#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
	digest = hashlib.sha256()
	with path.open("rb") as handle:
		while chunk := handle.read(1024 * 1024):
			digest.update(chunk)
	return digest.hexdigest()


def classify_backup_file(name: str) -> str | None:
	lowered = name.lower()
	if lowered.endswith(".sql.gz"):
		return "database"
	if "private-files" in lowered and lowered.endswith((".tar", ".tar.gz", ".tgz")):
		return "private_files"
	if "files" in lowered and lowered.endswith((".tar", ".tar.gz", ".tgz")):
		return "public_files"
	if "site_config" in lowered and lowered.endswith(".json"):
		return "site_config"
	return None


def verify_manifest(manifest_path: Path) -> dict[str, Any]:
	manifest_path = manifest_path.expanduser().resolve()
	if not manifest_path.is_file():
		raise RuntimeError(f"Backup manifest does not exist: {manifest_path}")

	payload = json.loads(manifest_path.read_text(encoding="utf-8"))
	if payload.get("format") != "construcontrol-local-backup-v1":
		raise RuntimeError("Unsupported backup manifest format.")
	if not str(payload.get("site") or "").strip():
		raise RuntimeError("Backup manifest has no site.")
	rows = payload.get("files")
	if not isinstance(rows, list) or not rows:
		raise RuntimeError("Backup manifest contains no files.")

	categories: dict[str, str] = {}
	verified: list[dict[str, Any]] = []
	total_bytes = 0
	for row in rows:
		if not isinstance(row, dict):
			raise RuntimeError("Backup manifest contains an invalid file row.")
		name = str(row.get("name") or "").strip()
		expected_size = int(row.get("bytes") or 0)
		expected_hash = str(row.get("sha256") or "").lower()
		if not name or Path(name).name != name:
			raise RuntimeError(f"Unsafe or empty backup filename: {name!r}")
		if expected_size <= 0:
			raise RuntimeError(f"Backup file has an invalid size: {name}")
		if not _SHA256.fullmatch(expected_hash):
			raise RuntimeError(f"Backup file has an invalid SHA-256: {name}")

		file_path = manifest_path.parent / name
		if not file_path.is_file():
			raise RuntimeError(f"Backup file is missing: {file_path}")
		actual_size = file_path.stat().st_size
		actual_hash = sha256_file(file_path)
		if actual_size != expected_size:
			raise RuntimeError(
				f"Backup size mismatch for {name}: expected {expected_size}, got {actual_size}"
			)
		if actual_hash != expected_hash:
			raise RuntimeError(f"Backup SHA-256 mismatch for {name}")

		category = classify_backup_file(name)
		if category:
			if category in categories:
				raise RuntimeError(f"Backup contains more than one {category} file.")
			categories[category] = str(file_path)
		verified.append(
			{
				"name": name,
				"bytes": actual_size,
				"sha256": actual_hash,
				"category": category,
			}
		)
		total_bytes += actual_size

	missing = [
		category
		for category in ("database", "public_files", "private_files", "site_config")
		if category not in categories
	]
	if missing:
		raise RuntimeError("Backup set is incomplete; missing: " + ", ".join(missing))

	return {
		"status": "verified",
		"manifest": str(manifest_path),
		"site": payload["site"],
		"files": verified,
		"categories": categories,
		"total_bytes": total_bytes,
	}


def main() -> int:
	parser = argparse.ArgumentParser(
		description="Verify a complete ConstruControl Bench backup set and every SHA-256."
	)
	parser.add_argument("--manifest", required=True, type=Path)
	parser.add_argument("--output", type=Path)
	args = parser.parse_args()

	result = verify_manifest(args.manifest)
	rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
	if args.output:
		args.output.expanduser().resolve().write_text(rendered, encoding="utf-8")
	print(rendered, end="")
	return 0


if __name__ == "__main__":
	try:
		raise SystemExit(main())
	except Exception as exc:
		print(f"Backup verification failed: {exc}", file=sys.stderr)
		raise SystemExit(1)
