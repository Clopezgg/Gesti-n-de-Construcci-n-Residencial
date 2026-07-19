from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_RUNTIME_ASSETS = Path(__file__).with_name("runtime") / "assets.json"
_PAGE_ROOT = Path(__file__).with_name("page")


def page_definitions() -> tuple[dict[str, Any], ...]:
	payload = json.loads(_RUNTIME_ASSETS.read_text(encoding="utf-8"))
	rows = payload.get("pages") or []
	return tuple(dict(row) for row in rows)


def page_script_path(page_name: str, page_root: Path = _PAGE_ROOT) -> Path:
	module_name = page_name.replace("-", "_")
	return page_root / module_name / f"{module_name}.js"


def canonical_page_values(definition: dict[str, Any]) -> dict[str, Any]:
	name = str(definition["name"])
	return {
		"doctype": "Page",
		"name": name,
		"page_name": str(definition.get("page_name") or name),
		"title": str(definition["title"]),
		"module": "ConstruControl",
		"standard": "No",
		"system_page": 0,
		# Frappe loads the controller from module/page/<scrubbed-name>/<scrubbed-name>.js.
		# Keeping the database script empty prevents stale parallel implementations.
		"script": "",
	}


def validate_page_contract(
	definitions: tuple[dict[str, Any], ...] | None = None,
	page_root: Path = _PAGE_ROOT,
) -> list[str]:
	rows = definitions or page_definitions()
	errors: list[str] = []
	seen: set[str] = set()
	for definition in rows:
		name = str(definition.get("name") or "").strip()
		if not name:
			errors.append("Page definition without name")
			continue
		if name in seen:
			errors.append(f"Duplicate canonical page: {name}")
		seen.add(name)
		if str(definition.get("page_name") or "") != name:
			errors.append(f"Page name mismatch: {name}")
		if definition.get("script") not in (None, ""):
			errors.append(f"Embedded page script is forbidden: {name}")
		roles = [str(role) for role in definition.get("roles") or []]
		if not roles or len(roles) != len(set(roles)):
			errors.append(f"Page roles must be non-empty and unique: {name}")
		script_path = page_script_path(name, page_root)
		if not script_path.is_file():
			errors.append(f"Missing canonical page controller: {script_path}")
			continue
		script = script_path.read_text(encoding="utf-8")
		if f'frappe.pages["{name}"]' not in script and f"frappe.pages['{name}']" not in script:
			errors.append(f"Controller does not register its canonical page: {name}")
	return errors


def ensure_canonical_pages() -> None:
	import frappe

	definitions = page_definitions()
	errors = validate_page_contract(definitions)
	if errors:
		raise RuntimeError("Invalid ConstruControl page contract: " + "; ".join(errors))

	for definition in definitions:
		name = str(definition["name"])
		exists = bool(frappe.db.exists("Page", name))
		values = canonical_page_values(definition)
		if exists:
			doc = frappe.get_doc("Page", name)
			for fieldname, value in values.items():
				if fieldname != "doctype":
					doc.set(fieldname, value)
			doc.set("roles", [])
		else:
			doc = frappe.get_doc(values)

		for role in definition["roles"]:
			doc.append("roles", {"role": role})
		if exists:
			doc.save(ignore_permissions=True)
		else:
			doc.insert(ignore_permissions=True)

	frappe.clear_cache()


__all__ = [
	"canonical_page_values",
	"ensure_canonical_pages",
	"page_definitions",
	"page_script_path",
	"validate_page_contract",
]
