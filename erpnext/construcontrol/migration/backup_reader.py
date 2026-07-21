from __future__ import annotations

import gzip
import io
import json
import re
import tarfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

MAX_BACKUP_BYTES = 64 * 1024 * 1024
COPY_PATTERN = re.compile(r'^COPY "(?P<schema>[^"]+)"\."(?P<table>[^"]+)" \((?P<columns>.*?)\) FROM stdin;$')

# Keys are stored in the same normalized form used by _sanitize: lowercase and
# without underscores. This prevents variants such as access_token or
# service_role_key from leaking into migration payloads.
SENSITIVE_KEYS = {
	"password",
	"passwordhash",
	"pinhash",
	"encryptedpassword",
	"confirmationtoken",
	"recoverytoken",
	"accesstoken",
	"refreshtoken",
	"servicerole",
	"servicerolekey",
	"supabaseservicerolekey",
	"clientsecret",
	"apisecret",
	"privatekey",
	"databasepassword",
}
IMAGE_CONTENT_KEYS = {"dataurl", "signaturedataurl"}
STORAGE_LOCATION_KEYS = {"storageurl", "storagepath"}


class BackupFormatError(ValueError):
	pass


def _copy_unescape(value: str) -> str | None:
	if value == r"\N":
		return None
	out: list[str] = []
	index = 0
	mapping = {"b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v", "\\": "\\"}
	while index < len(value):
		if value[index] != "\\":
			out.append(value[index])
			index += 1
			continue
		if index + 1 >= len(value):
			out.append("\\")
			index += 1
			continue
		char = value[index + 1]
		if char in mapping:
			out.append(mapping[char])
			index += 2
		elif char in "01234567":
			cursor = index + 1
			digits = ""
			while cursor < len(value) and len(digits) < 3 and value[cursor] in "01234567":
				digits += value[cursor]
				cursor += 1
			out.append(chr(int(digits, 8)))
			index = cursor
		elif char == "x" and index + 3 < len(value):
			hex_value = value[index + 2 : index + 4]
			try:
				out.append(chr(int(hex_value, 16)))
				index += 4
			except ValueError:
				out.append(char)
				index += 2
		else:
			out.append(char)
			index += 2
	return "".join(out)


def parse_copy_tables(
	sql_text: str,
	wanted: set[tuple[str, str]] | None = None,
) -> dict[tuple[str, str], list[dict[str, Any]]]:
	lines = iter(sql_text.splitlines())
	tables: dict[tuple[str, str], list[dict[str, Any]]] = {}
	for line in lines:
		match = COPY_PATTERN.match(line)
		if not match:
			continue
		key = (match.group("schema"), match.group("table"))
		columns = [item.strip().strip('"') for item in match.group("columns").split(",")]
		capture = wanted is None or key in wanted
		rows = tables.setdefault(key, []) if capture else None
		for row_line in lines:
			if row_line == r"\.":
				break
			if not capture:
				continue
			values = row_line.split("\t")
			if len(values) != len(columns):
				raise BackupFormatError(f"La tabla {key[0]}.{key[1]} contiene una fila inválida.")
			assert rows is not None
			rows.append(dict(zip(columns, (_copy_unescape(value) for value in values), strict=True)))
	return tables


def _read_backup_bytes(content: bytes, file_name: str) -> tuple[Any, str]:
	if len(content) > MAX_BACKUP_BYTES:
		raise BackupFormatError("El respaldo supera el límite de seguridad de 64 MiB.")
	lower = file_name.lower()
	if lower.endswith(".json"):
		return json.loads(content.decode("utf-8-sig")), "ConstruControl JSON"
	if lower.endswith(".sql"):
		return _payload_from_sql(content.decode("utf-8-sig")), "Supabase SQL"
	if lower.endswith((".tar.gz", ".tgz")):
		with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as archive:
			members = [
				member
				for member in archive.getmembers()
				if member.isfile() and Path(member.name).name == "data.sql"
			]
			if len(members) != 1:
				raise BackupFormatError("El paquete debe contener exactamente un archivo data.sql.")
			member = members[0]
			if member.size > MAX_BACKUP_BYTES:
				raise BackupFormatError("data.sql supera el límite de seguridad.")
			extracted = archive.extractfile(member)
			if not extracted:
				raise BackupFormatError("No se pudo leer data.sql.")
			data = extracted.read(MAX_BACKUP_BYTES + 1)
			if len(data) > MAX_BACKUP_BYTES:
				raise BackupFormatError("data.sql supera el límite de seguridad.")
			return _payload_from_sql(data.decode("utf-8-sig")), "Supabase Logical Backup"
	if lower.endswith(".gz"):
		data = gzip.decompress(content)
		if len(data) > MAX_BACKUP_BYTES:
			raise BackupFormatError("El SQL descomprimido supera el límite de seguridad.")
		return _payload_from_sql(data.decode("utf-8-sig")), "Supabase SQL Gzip"
	raise BackupFormatError("Formato no admitido. Use .tar.gz, .tgz, .sql, .sql.gz o .json.")


def _json_value(value: Any) -> Any:
	if not isinstance(value, str):
		return value
	try:
		return json.loads(value)
	except json.JSONDecodeError as exc:
		raise BackupFormatError(f"El JSON de construction_projects.data no es válido: {exc}") from exc


def _payload_from_sql(sql_text: str) -> dict[str, Any]:
	tables = parse_copy_tables(
		sql_text,
		wanted={("public", "construction_projects"), ("public", "app_user_profiles")},
	)
	projects = []
	for row in tables.get(("public", "construction_projects"), []):
		data = _json_value(row.get("data"))
		if not isinstance(data, Mapping):
			raise BackupFormatError("Una fila de construction_projects no contiene un objeto data válido.")
		projects.append(
			{
				"project_id": row.get("id"),
				"project_name": row.get("project_name"),
				"owner_name": row.get("owner_name"),
				"data": data,
				"created_at": row.get("created_at"),
				"updated_at": row.get("updated_at"),
			}
		)
	if not projects:
		raise BackupFormatError("El respaldo no contiene filas en public.construction_projects.")
	return {
		"format": "construcontrol-supabase-logical-backup-v1",
		"construction_projects": projects,
		"app_user_profiles": tables.get(("public", "app_user_profiles"), []),
	}


def _sanitize(value: Any, report: dict[str, int]) -> Any:
	if isinstance(value, list):
		return [_sanitize(item, report) for item in value]
	if not isinstance(value, Mapping):
		return value
	clean: dict[str, Any] = {}
	file_omitted = False
	for key, item in value.items():
		normalized = str(key).replace("_", "").replace("-", "").lower()
		if normalized in SENSITIVE_KEYS:
			report["secrets_removed"] += 1
			continue
		if normalized in IMAGE_CONTENT_KEYS:
			if item:
				report["image_payloads_removed"] += 1
				file_omitted = True
			continue
		if normalized in STORAGE_LOCATION_KEYS:
			if item:
				report["storage_locations_removed"] += 1
				file_omitted = True
			continue
		clean[str(key)] = _sanitize(item, report)
	if file_omitted:
		clean["_file_omitted"] = True
	return clean


def load_backup_content(content: bytes, file_name: str) -> tuple[Any, dict[str, Any]]:
	payload, source_kind = _read_backup_bytes(content, file_name)
	report = {
		"source_kind": source_kind,
		"source_file": Path(file_name).name,
		"images_imported": 0,
		"image_payloads_removed": 0,
		"storage_locations_removed": 0,
		"secrets_removed": 0,
	}
	return _sanitize(payload, report), report
