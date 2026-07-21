from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from erpnext.construcontrol.migration.importer import run_import
from erpnext.construcontrol.storage.supabase import download_object_to_path

MAX_MIGRATION_BUNDLE_BYTES = 2 * 1024 * 1024 * 1024
MAX_MIGRATION_UNCOMPRESSED_BYTES = 5 * 1024 * 1024 * 1024
MAX_MIGRATION_MEMBERS = 100_000


def _safe_extract_bundle(bundle_path: Path, destination: Path) -> Path:
	destination.mkdir(parents=True, exist_ok=True)
	with zipfile.ZipFile(bundle_path) as archive:
		members = archive.infolist()
		if len(members) > MAX_MIGRATION_MEMBERS:
			raise ValueError("Migration bundle contains too many files.")
		total = sum(member.file_size for member in members)
		if total > MAX_MIGRATION_UNCOMPRESSED_BYTES:
			raise ValueError("Migration bundle exceeds the uncompressed size limit.")
		archive_files: set[str] = set()
		for member in members:
			relative = Path(member.filename.replace("\\", "/"))
			if (
				relative.is_absolute()
				or not relative.parts
				or any(part in {"", ".", ".."} for part in relative.parts)
			):
				raise ValueError(f"Unsafe migration bundle path: {member.filename}")
			normalized = relative.as_posix().rstrip("/")
			if not member.is_dir():
				if normalized in archive_files:
					raise ValueError(f"Duplicate migration bundle member: {normalized}")
				archive_files.add(normalized)
			if member.flag_bits & 0x1:
				raise ValueError(f"Encrypted migration bundle members are not supported: {member.filename}")
			mode = member.external_attr >> 16
			if stat.S_ISLNK(mode):
				raise ValueError(f"Symlinks are not allowed in migration bundles: {member.filename}")
			target = (destination / relative).resolve()
			try:
				target.relative_to(destination.resolve())
			except ValueError as exc:
				raise ValueError(f"Migration bundle path escapes staging: {member.filename}") from exc
		archive.extractall(destination)

	manifest_path = destination / "bundle-manifest.json"
	if not manifest_path.is_file():
		raise ValueError("Migration bundle is missing bundle-manifest.json.")
	manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
	if manifest.get("format") != "construcontrol-migration-bundle-v1":
		raise ValueError("Unsupported migration bundle format.")
	items = manifest.get("files")
	if not isinstance(items, list) or not items:
		raise ValueError("Migration bundle manifest contains no files.")
	manifest_files: set[str] = set()
	for item in items:
		if not isinstance(item, dict) or not item.get("path"):
			raise ValueError("Migration bundle manifest contains an invalid row.")
		relative = Path(str(item["path"]).replace("\\", "/"))
		if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
			raise ValueError(f"Unsafe manifest path: {relative}")
		normalized = relative.as_posix()
		if normalized in manifest_files:
			raise ValueError(f"Duplicate migration manifest path: {normalized}")
		manifest_files.add(normalized)
		candidate = (destination / relative).resolve()
		try:
			candidate.relative_to(destination.resolve())
		except ValueError as exc:
			raise ValueError(f"Manifest path escapes migration bundle: {relative}") from exc
		if not candidate.is_file():
			raise ValueError(f"Manifest file is missing: {relative}")
		digest = hashlib.sha256()
		size = 0
		with candidate.open("rb") as handle:
			while chunk := handle.read(1024 * 1024):
				digest.update(chunk)
				size += len(chunk)
		if item.get("bytes") is not None and size != cint(item.get("bytes")):
			raise ValueError(f"Manifest file size mismatch: {relative}")
		if item.get("sha256") and digest.hexdigest() != item.get("sha256"):
			raise ValueError(f"Manifest checksum mismatch: {relative}")

	expected_archive_files = archive_files - {"bundle-manifest.json"}
	if manifest_files != expected_archive_files:
		missing = sorted(expected_archive_files - manifest_files)
		unexpected = sorted(manifest_files - expected_archive_files)
		raise ValueError(
			f"Migration bundle manifest/file mismatch; unlisted={missing[:5]}, missing={unexpected[:5]}"
		)

	exports = list(destination.rglob("construcontrol-supabase-export.json"))
	if len(exports) != 1:
		raise ValueError(
			"Migration bundle must contain exactly one construcontrol-supabase-export.json file."
		)
	return exports[0]


def run_import_from_supabase(
	object_key: str,
	dry_run: bool = True,
	source_kind: str = "Supabase Export",
	backup_reference: str | None = None,
	bucket: str | None = None,
) -> dict[str, Any]:
	"""Download, verify, import and discard one private migration bundle."""
	bucket_name = bucket or os.getenv("SUPABASE_MIGRATION_BUCKET", "construcontrol-migration")
	if not object_key or not object_key.lower().endswith(".zip"):
		frappe.throw(_("The migration object key must point to a .zip bundle."))
	with tempfile.TemporaryDirectory(prefix="construcontrol-migration-") as temporary:
		root = Path(temporary)
		bundle_path = root / "migration-bundle.zip"
		download = download_object_to_path(
			bucket_name,
			object_key,
			bundle_path,
			max_bytes=MAX_MIGRATION_BUNDLE_BYTES,
		)
		export_path = _safe_extract_bundle(bundle_path, root / "extracted")
		result = run_import(
			str(export_path),
			dry_run=dry_run,
			source_kind=source_kind,
			backup_reference=backup_reference,
		)
		result["bundle_bucket"] = bucket_name
		result["bundle_object_key"] = object_key
		result["bundle_sha256"] = download["sha256"]
		return result
