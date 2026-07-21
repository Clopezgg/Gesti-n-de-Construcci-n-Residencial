#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path


def sha256_file(path: Path) -> str:
	digest = hashlib.sha256()
	with path.open("rb") as handle:
		while chunk := handle.read(1024 * 1024):
			digest.update(chunk)
	return digest.hexdigest()


def main() -> int:
	parser = argparse.ArgumentParser(
		description="Create a validated private ConstruControl migration ZIP bundle."
	)
	parser.add_argument("source_directory", type=Path)
	parser.add_argument("output_zip", type=Path)
	args = parser.parse_args()

	source = args.source_directory.expanduser().resolve()
	output = args.output_zip.expanduser().resolve()
	if not source.is_dir():
		raise RuntimeError(f"Source directory does not exist: {source}")
	if output == source or source in output.parents:
		raise RuntimeError("The output ZIP must be outside the export directory.")

	export_file = source / "construcontrol-supabase-export.json"
	manifest_file = source / "storage-manifest.json"
	if not export_file.is_file():
		raise RuntimeError(f"Missing required export: {export_file}")
	if not manifest_file.is_file():
		raise RuntimeError(f"Missing required Storage manifest: {manifest_file}")

	report_file = source / "preflight-report.json"
	validator = Path(__file__).resolve().with_name("validate_construcontrol_backup.py")
	subprocess.run(
		[sys.executable, str(validator), str(export_file), "--report", str(report_file)],
		check=True,
		stdout=subprocess.PIPE,
		text=True,
	)

	files: list[Path] = []
	for path in sorted(source.rglob("*")):
		if path.is_symlink():
			raise RuntimeError(f"Symlinks are not allowed in migration bundles: {path}")
		if path.is_file():
			files.append(path)
	if not files:
		raise RuntimeError("The export directory is empty.")

	bundle_manifest = {
		"format": "construcontrol-migration-bundle-v1",
		"source_directory": source.name,
		"files": [
			{
				"path": path.relative_to(source).as_posix(),
				"bytes": path.stat().st_size,
				"sha256": sha256_file(path),
			}
			for path in files
		],
	}
	output.parent.mkdir(parents=True, exist_ok=True)
	temporary = output.with_suffix(output.suffix + ".tmp")
	temporary.unlink(missing_ok=True)
	with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
		for path in files:
			archive.write(path, path.relative_to(source).as_posix())
		archive.writestr(
			"bundle-manifest.json",
			json.dumps(bundle_manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
		)
	os.replace(temporary, output)
	result = {
		"bundle": str(output),
		"bytes": output.stat().st_size,
		"sha256": sha256_file(output),
		"file_count": len(files),
	}
	print(json.dumps(result, ensure_ascii=False, indent=2))
	return 0


if __name__ == "__main__":
	try:
		raise SystemExit(main())
	except Exception as exc:
		print(f"Bundle creation failed: {exc}", file=sys.stderr)
		raise SystemExit(1)
