from __future__ import annotations

import re
import unicodedata
from typing import Any

import frappe

INTEGRATION_NAMES = (
    "ERPNext Integrations",
    "Integrations",
    "Integrations NEXT",
    "Integraciones",
    "Integraciones NEXT",
)


def _normalized_workspace_value(value: Any) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value or ""))
    without_marks = "".join(character for character in decomposed if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", " ", without_marks.casefold()).strip()


_INTEGRATION_KEYS = {_normalized_workspace_value(name) for name in INTEGRATION_NAMES}
_PREFERRED_KEYS = tuple(_normalized_workspace_value(name) for name in INTEGRATION_NAMES)


def _row_key(row: Any) -> tuple[str, ...]:
    return tuple(
        str(row.get(field) or "").strip().casefold()
        for field in ("label", "link_to", "link_type", "type", "shortcut_name")
    )


def _merge_child_rows(canonical: Any, duplicate: Any, fieldname: str) -> int:
    if not canonical.meta.has_field(fieldname) or not duplicate.meta.has_field(fieldname):
        return 0
    existing = {_row_key(row) for row in canonical.get(fieldname) or []}
    added = 0
    for row in duplicate.get(fieldname) or []:
        values = {
            field.fieldname: row.get(field.fieldname)
            for field in row.meta.fields
            if field.fieldname
            and field.fieldname not in {"name", "parent", "parentfield", "parenttype", "idx", "doctype"}
        }
        key = _row_key(values)
        if key in existing:
            continue
        canonical.append(fieldname, values)
        existing.add(key)
        added += 1
    return added


def _integration_workspace_names() -> list[str]:
    rows = frappe.get_all("Workspace", fields=["name", "label", "title"])
    names: list[str] = []
    for row in rows:
        values = (row.get("name"), row.get("label"), row.get("title"))
        if any(_normalized_workspace_value(value) in _INTEGRATION_KEYS for value in values):
            name = str(row.get("name") or "").strip()
            if name and name not in names:
                names.append(name)
    return names


def _canonical_rank(name: str) -> tuple[int, str]:
    key = _normalized_workspace_value(name)
    try:
        position = _PREFERRED_KEYS.index(key)
    except ValueError:
        position = len(_PREFERRED_KEYS)
    return position, key


def _set_workspace_visibility(doc: Any, *, visible: bool) -> None:
    if doc.meta.has_field("is_hidden"):
        doc.is_hidden = 0 if visible else 1
    if doc.meta.has_field("public"):
        doc.public = 1 if visible else 0


def consolidate_integration_workspaces() -> dict[str, Any]:
    """Expose exactly one Integraciones workspace and preserve unique links."""
    if not frappe.db.exists("DocType", "Workspace"):
        return {"canonical": None, "hidden": [], "merged_rows": 0}

    existing = _integration_workspace_names()
    if not existing:
        return {"canonical": None, "hidden": [], "merged_rows": 0}

    canonical_name = min(existing, key=_canonical_rank)
    canonical = frappe.get_doc("Workspace", canonical_name)
    merged_rows = 0
    hidden: list[str] = []

    for name in existing:
        if name == canonical_name:
            continue
        duplicate = frappe.get_doc("Workspace", name)
        for fieldname in ("links", "shortcuts", "charts", "number_cards"):
            merged_rows += _merge_child_rows(canonical, duplicate, fieldname)
        _set_workspace_visibility(duplicate, visible=False)
        duplicate.save(ignore_permissions=True)
        hidden.append(name)

    if canonical.meta.has_field("label"):
        canonical.label = "Integraciones"
    if canonical.meta.has_field("title"):
        canonical.title = "Integraciones"
    _set_workspace_visibility(canonical, visible=True)
    canonical.save(ignore_permissions=True)
    frappe.clear_cache()

    return {"canonical": canonical_name, "hidden": hidden, "merged_rows": merged_rows}
