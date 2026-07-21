#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

EXACT_SHA = re.compile(r"^[0-9a-f]{40}$", re.I)
EXACT_SHA256 = re.compile(r"^[0-9a-f]{64}$", re.I)
REQUIRED_RECEIPT_FIELDS = {
	"schema_version",
	"requirement_id",
	"cert_sha",
	"module",
	"implementation",
	"command",
	"test",
	"scenarios",
	"result",
	"artifact",
	"receipt_sha256",
}


def sha256_file(path: Path) -> str:
	digest = hashlib.sha256()
	with path.open("rb") as handle:
		while chunk := handle.read(1024 * 1024):
			digest.update(chunk)
	return digest.hexdigest()


def artifact_manifest(path: Path) -> list[dict[str, Any]]:
	path = path.resolve()
	if path.is_file():
		return [{"path": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)}]
	if not path.is_dir():
		raise FileNotFoundError(f"Artifact does not exist: {path}")
	rows = []
	for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
		rows.append(
			{
				"path": item.relative_to(path).as_posix(),
				"bytes": item.stat().st_size,
				"sha256": sha256_file(item),
			}
		)
	if not rows:
		raise ValueError(f"Artifact is empty: {path}")
	return rows


def artifact_digest(path: Path) -> tuple[str, list[dict[str, Any]]]:
	manifest = artifact_manifest(path)
	payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
	return hashlib.sha256(payload).hexdigest(), manifest


def receipt_digest(receipt: dict[str, Any]) -> str:
	payload = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
	canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
	return hashlib.sha256(canonical).hexdigest()


__all__ = [
	"EXACT_SHA",
	"EXACT_SHA256",
	"REQUIRED_RECEIPT_FIELDS",
	"artifact_digest",
	"artifact_manifest",
	"receipt_digest",
	"sha256_file",
]
