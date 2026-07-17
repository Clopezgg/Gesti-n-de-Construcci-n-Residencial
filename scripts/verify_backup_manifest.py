#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a ConstruControl local backup manifest.")
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()

    manifest_path = args.manifest.expanduser().resolve()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("format") != "construcontrol-local-backup-v1":
        raise RuntimeError("Unsupported backup manifest format.")
    rows = payload.get("files")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("The backup manifest contains no files.")

    errors: list[str] = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("name"):
            errors.append("Invalid file row in manifest.")
            continue
        path = manifest_path.parent / str(row["name"])
        if not path.is_file():
            errors.append(f"Missing file: {path.name}")
            continue
        if path.stat().st_size != int(row.get("bytes", -1)):
            errors.append(f"Size mismatch: {path.name}")
        if sha256_file(path) != row.get("sha256"):
            errors.append(f"SHA-256 mismatch: {path.name}")

    result = {
        "manifest": str(manifest_path),
        "verified_files": len(rows) - len(errors),
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Backup verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
