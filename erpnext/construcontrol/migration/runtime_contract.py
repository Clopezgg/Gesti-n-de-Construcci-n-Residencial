from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

CONTRACT_VERSION = 1
_ALLOWED_DOCTYPE_PREFIXES = ("CC ", "ConstruControl ")
_FIELDNAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_REQUIRED_ASSET_GROUPS = ("pages", "reports", "print_formats")
_LINK_FIELD_TYPES = {"Link", "Table", "Table MultiSelect"}
_DESTRUCTIVE_KEYS = {
	"delete_existing",
	"drop_column",
	"drop_columns",
	"drop_table",
	"drop_tables",
	"reset_database",
	"truncate",
	"truncate_table",
}
_PROVENANCE_FIELDS = ("source_key", "source_id", "payload_json", "is_logically_deleted")


def _canonical_json(value: Any) -> str:
	return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value: Any) -> str:
	return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _destructive_paths(value: Any, prefix: str = "") -> list[str]:
	paths: list[str] = []
	if isinstance(value, Mapping):
		for key, item in value.items():
			key_text = str(key)
			path = f"{prefix}.{key_text}" if prefix else key_text
			if key_text.casefold() in _DESTRUCTIVE_KEYS and item not in (None, False, 0, "", [], {}):
				paths.append(path)
			paths.extend(_destructive_paths(item, path))
	elif isinstance(value, list):
		for index, item in enumerate(value):
			path = f"{prefix}[{index}]" if prefix else f"[{index}]"
			paths.extend(_destructive_paths(item, path))
	return paths


def _asset_name(group: str, row: Mapping[str, Any]) -> str:
	if group == "pages":
		return str(row.get("name") or row.get("page_name") or "").strip()
	if group == "reports":
		return str(row.get("name") or row.get("report_name") or "").strip()
	return str(row.get("name") or "").strip()


def load_runtime_contract(runtime_dir: str | Path) -> dict[str, Any]:
	root = Path(runtime_dir)
	definition_files = sorted(root.glob("definitions_*.json"))
	if not definition_files:
		raise ValueError(f"No se encontraron definiciones runtime en {root}")

	definitions: list[dict[str, Any]] = []
	source_files: list[str] = []
	for path in definition_files:
		payload = json.loads(path.read_text(encoding="utf-8"))
		if not isinstance(payload, list):
			raise ValueError(f"{path.name} debe contener una lista JSON")
		for row in payload:
			if not isinstance(row, Mapping):
				raise ValueError(f"{path.name} contiene una definición que no es un objeto")
			definitions.append(dict(row))
		source_files.append(path.name)

	assets_path = root / "assets.json"
	if not assets_path.is_file():
		raise ValueError(f"No se encontró {assets_path}")
	assets = json.loads(assets_path.read_text(encoding="utf-8"))
	if not isinstance(assets, Mapping):
		raise ValueError("assets.json debe contener un objeto JSON")

	contract = {
		"version": CONTRACT_VERSION,
		"definition_files": source_files,
		"definitions": definitions,
		"assets": dict(assets),
	}
	contract["sha256"] = _digest(contract)
	return contract


def validate_runtime_contract(
	runtime_dir: str | Path,
	*,
	required_doctypes: Iterable[str] = (),
) -> dict[str, Any]:
	errors: list[str] = []
	warnings: list[str] = []

	try:
		contract = load_runtime_contract(runtime_dir)
	except (OSError, ValueError, json.JSONDecodeError) as exc:
		return {
			"ok": False,
			"contract_version": CONTRACT_VERSION,
			"sha256": None,
			"doctype_count": 0,
			"asset_count": 0,
			"errors": [str(exc)],
			"warnings": [],
		}

	definitions = contract["definitions"]
	names: set[str] = set()
	fields_by_doctype: dict[str, dict[str, Mapping[str, Any]]] = {}

	for index, definition in enumerate(definitions, start=1):
		name = str(definition.get("name") or "").strip()
		location = f"definición #{index}"
		if not name:
			errors.append(f"{location}: falta name")
			continue
		if name in names:
			errors.append(f"DocType duplicado: {name}")
			continue
		names.add(name)

		if not name.startswith(_ALLOWED_DOCTYPE_PREFIXES):
			errors.append(f"{name}: una definición runtime no puede modificar un DocType estándar de ERPNext")

		if definition.get("custom") not in (None, 1, True):
			errors.append(f"{name}: las definiciones runtime deben ser DocTypes personalizados")

		destructive = _destructive_paths(definition)
		if destructive:
			errors.append(f"{name}: contiene operaciones destructivas: {', '.join(destructive)}")

		rows = definition.get("fields") or []
		if not isinstance(rows, list):
			errors.append(f"{name}: fields debe ser una lista")
			continue

		field_map: dict[str, Mapping[str, Any]] = {}
		for field_index, field in enumerate(rows, start=1):
			if not isinstance(field, Mapping):
				errors.append(f"{name}.fields[{field_index}]: debe ser un objeto")
				continue
			fieldname = str(field.get("fieldname") or "").strip()
			fieldtype = str(field.get("fieldtype") or "").strip()
			if not fieldname:
				errors.append(f"{name}.fields[{field_index}]: falta fieldname")
				continue
			if not _FIELDNAME_PATTERN.fullmatch(fieldname):
				errors.append(f"{name}.{fieldname}: fieldname no válido")
			if fieldname in field_map:
				errors.append(f"{name}: fieldname duplicado: {fieldname}")
				continue
			field_map[fieldname] = field
			if not fieldtype:
				errors.append(f"{name}.{fieldname}: falta fieldtype")
			if fieldtype in _LINK_FIELD_TYPES and not str(field.get("options") or "").strip():
				errors.append(f"{name}.{fieldname}: {fieldtype} requiere options")

		fields_by_doctype[name] = field_map

	required = {str(name).strip() for name in required_doctypes if str(name).strip()}
	missing_required = sorted(required - names)
	if missing_required:
		errors.append("Faltan DocTypes usados por el importador: " + ", ".join(missing_required))

	for name in sorted(required & names):
		field_map = fields_by_doctype.get(name, {})
		missing_provenance = [field for field in _PROVENANCE_FIELDS if field not in field_map]
		if missing_provenance:
			errors.append(f"{name}: faltan campos de trazabilidad: {', '.join(missing_provenance)}")
		source_key = field_map.get("source_key")
		if source_key and str(source_key.get("fieldtype") or "") != "Data":
			errors.append(f"{name}.source_key debe ser Data")
		if source_key and not bool(source_key.get("unique")):
			warnings.append(f"{name}.source_key aún no está marcado como único")

	assets = contract["assets"]
	asset_count = 0
	for group in _REQUIRED_ASSET_GROUPS:
		rows = assets.get(group)
		if not isinstance(rows, list):
			errors.append(f"assets.json: {group} debe ser una lista")
			continue
		seen: set[str] = set()
		for index, row in enumerate(rows, start=1):
			if not isinstance(row, Mapping):
				errors.append(f"assets.json {group}[{index}]: debe ser un objeto")
				continue
			name = _asset_name(group, row)
			if not name:
				errors.append(f"assets.json {group}[{index}]: falta nombre")
				continue
			if name in seen:
				errors.append(f"assets.json: {group} duplicado: {name}")
			seen.add(name)
			destructive = _destructive_paths(row)
			if destructive:
				errors.append(f"assets.json {group} {name}: contiene operaciones destructivas")
		asset_count += len(rows)

	return {
		"ok": not errors,
		"contract_version": CONTRACT_VERSION,
		"sha256": contract["sha256"],
		"doctype_count": len(names),
		"asset_count": asset_count,
		"required_doctypes": len(required),
		"errors": errors,
		"warnings": warnings,
	}


def validate_runtime_contract_or_raise(
	runtime_dir: str | Path,
	*,
	required_doctypes: Iterable[str] = (),
) -> dict[str, Any]:
	report = validate_runtime_contract(runtime_dir, required_doctypes=required_doctypes)
	if not report["ok"]:
		raise RuntimeError("Contrato runtime ConstruControl inválido: " + "; ".join(report["errors"]))
	return report


__all__ = [
	"CONTRACT_VERSION",
	"load_runtime_contract",
	"validate_runtime_contract",
	"validate_runtime_contract_or_raise",
]
