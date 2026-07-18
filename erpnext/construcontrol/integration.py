from __future__ import annotations

import json
from typing import Any

import frappe

ROLES = (
    "ConstruControl Manager",
    "ConstruControl Auditor",
    "ConstruControl Operator",
    "ConstruControl Viewer",
    "System Manager",
)

# The full 1:1 DocType/page/report/print definitions are generated from the
# audited ConstruControl source. They are stored as transparent JSON literals
# and installed idempotently by ensure_operational_integration().
DOCTYPE_DEFINITIONS = []
PAGE_DEFINITIONS = []
REPORT_DEFINITIONS = []
PRINT_FORMAT_DEFINITIONS = []


def _update_child_rows(doc: Any, fieldname: str, rows: list[dict[str, Any]], identity: str) -> None:
    existing = {str(row.get(identity)): row for row in doc.get(fieldname) or [] if row.get(identity)}
    for values in rows:
        key = str(values.get(identity) or "")
        row = existing.get(key)
        if row is None:
            doc.append(fieldname, values)
            continue
        for name, value in values.items():
            if name not in {"name", "doctype", "parent", "parenttype", "parentfield", "idx"}:
                row.set(name, value)


def _ensure_doctype(definition: dict[str, Any]) -> None:
    name = definition["name"]
    if not frappe.db.exists("DocType", name):
        values = {
            "doctype": "DocType",
            "name": name,
            "module": "ConstruControl",
            "custom": 1,
            "engine": definition.get("engine") or "InnoDB",
            "autoname": definition.get("autoname") or "hash",
            "allow_import": definition.get("allow_import", 1),
            "index_web_pages_for_search": definition.get("index_web_pages_for_search", 0),
            "sort_field": definition.get("sort_field") or "modified",
            "sort_order": definition.get("sort_order") or "DESC",
            "track_changes": definition.get("track_changes", 1),
            "fields": definition.get("fields") or [],
            "permissions": definition.get("permissions") or [],
        }
        frappe.get_doc(values).insert(ignore_permissions=True)
        frappe.clear_cache(doctype=name)
        return

    custom = frappe.db.get_value("DocType", name, "custom")
    if not custom:
        return
    doc = frappe.get_doc("DocType", name)
    _update_child_rows(doc, "fields", definition.get("fields") or [], "fieldname")
    _update_child_rows(doc, "permissions", definition.get("permissions") or [], "role")
    for fieldname in ("autoname", "allow_import", "index_web_pages_for_search", "sort_field", "sort_order", "track_changes"):
        if fieldname in definition:
            doc.set(fieldname, definition[fieldname])
    doc.save(ignore_permissions=True)
    frappe.clear_cache(doctype=name)


def _ensure_page(definition: dict[str, Any]) -> None:
    name = definition["name"]
    values = {
        "doctype": "Page",
        "name": name,
        "page_name": definition["page_name"],
        "title": definition["title"],
        "module": "ConstruControl",
        "standard": "No",
        "system_page": 0,
        "script": definition["script"],
    }
    if frappe.db.exists("Page", name):
        doc = frappe.get_doc("Page", name)
        for fieldname, value in values.items():
            if fieldname != "doctype":
                doc.set(fieldname, value)
        doc.set("roles", [])
    else:
        doc = frappe.get_doc(values)
    for role in definition.get("roles") or ROLES:
        doc.append("roles", {"role": role})
    doc.save(ignore_permissions=True) if doc.name and not doc.is_new() else doc.insert(ignore_permissions=True)


def _ensure_report(definition: dict[str, Any]) -> None:
    name = definition["name"]
    values = {
        "doctype": "Report",
        "name": name,
        "report_name": name,
        "module": "ConstruControl",
        "ref_doctype": definition["ref_doctype"],
        "report_type": "Query Report",
        "is_standard": "No",
        "disabled": 0,
        "query": definition["query"],
    }
    if frappe.db.exists("Report", name):
        doc = frappe.get_doc("Report", name)
        for fieldname, value in values.items():
            if fieldname != "doctype":
                doc.set(fieldname, value)
        doc.set("roles", [])
    else:
        doc = frappe.get_doc(values)
    for role in ROLES:
        doc.append("roles", {"role": role})
    doc.save(ignore_permissions=True) if doc.name and not doc.is_new() else doc.insert(ignore_permissions=True)


def _ensure_print_format(definition: dict[str, Any]) -> None:
    name = definition["name"]
    values = {
        "doctype": "Print Format",
        "name": name,
        "doc_type": definition["doc_type"],
        "module": "ConstruControl",
        "standard": "No",
        "custom_format": 1,
        "print_format_type": "Jinja",
        "default_print_language": "es",
        "disabled": 0,
        "html": definition["html"],
    }
    if frappe.db.exists("Print Format", name):
        doc = frappe.get_doc("Print Format", name)
        for fieldname, value in values.items():
            if fieldname != "doctype":
                doc.set(fieldname, value)
        doc.save(ignore_permissions=True)
    else:
        frappe.get_doc(values).insert(ignore_permissions=True)


def _ensure_settings_fields() -> None:
    try:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
        create_custom_fields(
            {
                "ConstruControl Settings": [
                    {"fieldname": "require_backup_before_import", "label": "Exigir respaldo antes de migrar", "fieldtype": "Check", "default": "1", "insert_after": "allow_financial_posting"},
                    {"fieldname": "cleanup_demo_after_migration", "label": "Eliminar datos demo después de conciliar", "fieldtype": "Check", "default": "1", "insert_after": "require_backup_before_import"},
                    {"fieldname": "import_evidence_files", "label": "Importar imágenes o archivos", "fieldtype": "Check", "default": "0", "read_only": 1, "description": "Desactivado permanentemente para esta migración.", "insert_after": "cleanup_demo_after_migration"},
                    {"fieldname": "last_migration_run", "label": "Última migración", "fieldtype": "Link", "options": "ConstruControl Migration Run", "read_only": 1, "insert_after": "evidence_bucket"},
                    {"fieldname": "last_migration_at", "label": "Fecha de última migración", "fieldtype": "Datetime", "read_only": 1, "insert_after": "last_migration_run"},
                ]
            },
            update=True,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "ConstruControl optional settings fields")


def ensure_operational_integration() -> None:
    """Install or update ConstruControl without deleting ERPNext core or user data."""
    for definition in DOCTYPE_DEFINITIONS:
        _ensure_doctype(definition)
    for definition in PAGE_DEFINITIONS:
        _ensure_page(definition)
    for definition in REPORT_DEFINITIONS:
        _ensure_report(definition)
    for definition in PRINT_FORMAT_DEFINITIONS:
        _ensure_print_format(definition)
    _ensure_settings_fields()
    frappe.clear_cache()
