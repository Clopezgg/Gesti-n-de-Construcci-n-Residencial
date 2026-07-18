from __future__ import annotations

from typing import Any

import frappe

INTEGRATION_NAMES = (
    "ERPNext Integrations",
    "Integrations",
    "Integrations NEXT",
    "Integraciones",
    "Integraciones NEXT",
)


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


def consolidate_integration_workspaces() -> dict[str, Any]:
    """Keep one integrations workspace while preserving unique links from duplicates."""
    if not frappe.db.exists("DocType", "Workspace"):
        return {"canonical": None, "hidden": [], "merged_rows": 0}

    existing = [name for name in INTEGRATION_NAMES if frappe.db.exists("Workspace", name)]
    if len(existing) < 2:
        return {"canonical": existing[0] if existing else None, "hidden": [], "merged_rows": 0}

    canonical_name = "ERPNext Integrations" if "ERPNext Integrations" in existing else existing[0]
    canonical = frappe.get_doc("Workspace", canonical_name)
    merged_rows = 0
    hidden: list[str] = []

    for name in existing:
        if name == canonical_name:
            continue
        duplicate = frappe.get_doc("Workspace", name)
        for fieldname in ("links", "shortcuts", "charts", "number_cards"):
            merged_rows += _merge_child_rows(canonical, duplicate, fieldname)

        if duplicate.meta.has_field("is_hidden"):
            duplicate.db_set("is_hidden", 1, update_modified=False)
        elif duplicate.meta.has_field("public"):
            duplicate.db_set("public", 0, update_modified=False)
        hidden.append(name)

    if canonical.meta.has_field("label"):
        canonical.label = "Integraciones"
    if canonical.meta.has_field("title"):
        canonical.title = "Integraciones"
    canonical.save(ignore_permissions=True)
    frappe.clear_cache()

    return {"canonical": canonical_name, "hidden": hidden, "merged_rows": merged_rows}
