from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import frappe

ROLES = (
    "ConstruControl Manager",
    "ConstruControl Auditor",
    "ConstruControl Operator",
    "ConstruControl Viewer",
    "System Manager",
)

_RUNTIME = Path(__file__).with_name("runtime")
_AUDIT_ONLY_DOCTYPES = {
    "CC Audit Log",
    "CC Immutable Audit Event",
    "CC Backup Snapshot",
    "CC Notification Log",
    "CC Automation Execution",
}


def _load_json(name: str) -> Any:
    return json.loads((_RUNTIME / name).read_text(encoding="utf-8"))


def _doctype_definitions() -> list[dict[str, Any]]:
    definitions: list[dict[str, Any]] = []
    for path in sorted(_RUNTIME.glob("definitions_*.json")):
        definitions.extend(json.loads(path.read_text(encoding="utf-8")))

    priority = {
        name: index
        for index, name in enumerate(
            (
                "CC Project Profile",
                "CC Construction Phase",
                "CC Funding Source",
                "CC Labor Contract",
                "CC Material Ledger",
                "CC Business Partner Profile",
                "CC Crew Member",
                "CC Equipment Control",
                "CC Expense Control",
                "CC Inventory Movement",
                "CC Progress Update",
                "CC Weekly Closing",
                "CC Evidence",
                "CC Audit Log",
                "CC User Access",
            )
        )
    }
    definitions.sort(key=lambda row: (priority.get(row.get("name"), 1000), str(row.get("name") or "")))
    return definitions


def _update_fields(doc: Any, rows: list[dict[str, Any]]) -> None:
    existing = {str(row.fieldname): row for row in doc.fields if row.fieldname}
    for values in rows:
        fieldname = str(values.get("fieldname") or "")
        row = existing.get(fieldname)
        if row is None:
            doc.append("fields", values)
            continue
        for name, value in values.items():
            if name not in {"name", "doctype", "parent", "parenttype", "parentfield", "idx"}:
                row.set(name, value)


def _secure_permissions(definition: dict[str, Any]) -> list[dict[str, Any]]:
    """Return one exact, least-privilege permission row per ConstruControl role."""
    audit_only = str(definition.get("name") or "") in _AUDIT_ONLY_DOCTYPES
    permissions: list[dict[str, Any]] = [
        {
            "role": "System Manager",
            "read": 1,
            "write": 1,
            "create": 1,
            "delete": 1,
            "print": 1,
            "email": 1,
            "export": 1,
            "share": 1,
        },
        {
            "role": "ConstruControl Manager",
            "read": 1,
            "write": 0 if audit_only else 1,
            "create": 0 if audit_only else 1,
            "delete": 0,
            "print": 1,
            "email": 0 if audit_only else 1,
            "export": 1,
            "share": 0,
        },
        {
            "role": "ConstruControl Auditor",
            "read": 1,
            "write": 0,
            "create": 0,
            "delete": 0,
            "print": 1,
            "email": 0,
            "export": 1,
            "share": 0,
        },
        {
            "role": "ConstruControl Viewer",
            "read": 1,
            "write": 0,
            "create": 0,
            "delete": 0,
            "print": 0,
            "email": 0,
            "export": 0,
            "share": 0,
        },
    ]
    permissions.insert(
        2,
        {
            "role": "ConstruControl Operator",
            "read": 1,
            "write": 0 if audit_only else 1,
            "create": 0 if audit_only else 1,
            "delete": 0,
            "print": 0,
            "email": 0,
            "export": 0,
            "share": 0,
        },
    )
    return permissions


def _replace_permissions(doc: Any, rows: list[dict[str, Any]]) -> None:
    doc.set("permissions", [])
    for values in rows:
        doc.append("permissions", values)


def _ensure_doctype(definition: dict[str, Any]) -> None:
    name = definition["name"]
    permissions = _secure_permissions(definition)

    if not frappe.db.exists("DocType", name):
        frappe.get_doc(
            {
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
                "title_field": definition.get("title_field"),
                "search_fields": definition.get("search_fields"),
                "show_title_field_in_link": definition.get("show_title_field_in_link", 0),
                "fields": definition.get("fields") or [],
                "permissions": permissions,
            }
        ).insert(ignore_permissions=True)
        frappe.clear_cache(doctype=name)
        return

    if not frappe.db.get_value("DocType", name, "custom"):
        return

    doc = frappe.get_doc("DocType", name)
    _update_fields(doc, definition.get("fields") or [])
    _replace_permissions(doc, permissions)
    for fieldname in (
        "autoname",
        "allow_import",
        "index_web_pages_for_search",
        "sort_field",
        "sort_order",
        "track_changes",
        "title_field",
        "search_fields",
        "show_title_field_in_link",
    ):
        if fieldname in definition:
            doc.set(fieldname, definition[fieldname])
    doc.save(ignore_permissions=True)
    frappe.clear_cache(doctype=name)


def _save_or_insert(doc: Any, *, exists: bool) -> None:
    """Persist records using the database existence check as the source of truth."""
    if exists:
        doc.save(ignore_permissions=True)
    else:
        doc.insert(ignore_permissions=True)


def _ensure_page(definition: dict[str, Any]) -> None:
    name = definition["name"]
    exists = bool(frappe.db.exists("Page", name))
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
    if exists:
        doc = frappe.get_doc("Page", name)
        for fieldname, value in values.items():
            if fieldname != "doctype":
                doc.set(fieldname, value)
        doc.set("roles", [])
    else:
        doc = frappe.get_doc(values)

    page_roles = ["System Manager"] if name == "construcontrol-migration-console" else list(definition.get("roles") or ROLES)
    for role in page_roles:
        doc.append("roles", {"role": role})
    _save_or_insert(doc, exists=exists)


def _ensure_report(definition: dict[str, Any]) -> None:
    name = definition["name"]
    exists = bool(frappe.db.exists("Report", name))
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
    if exists:
        doc = frappe.get_doc("Report", name)
        for fieldname, value in values.items():
            if fieldname != "doctype":
                doc.set(fieldname, value)
        doc.set("roles", [])
    else:
        doc = frappe.get_doc(values)
    for role in ROLES:
        doc.append("roles", {"role": role})
    _save_or_insert(doc, exists=exists)


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


def _ensure_custom_fields() -> None:
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields(
        {
            "ConstruControl Settings": [
                {"fieldname": "require_backup_before_import", "label": "Exigir respaldo antes de migrar", "fieldtype": "Check", "default": "1", "insert_after": "allow_financial_posting"},
                {"fieldname": "cleanup_demo_after_migration", "label": "Eliminar datos demo después de conciliar", "fieldtype": "Check", "default": "1", "insert_after": "require_backup_before_import"},
                {"fieldname": "import_evidence_files", "label": "Importar imágenes o archivos históricos", "fieldtype": "Check", "default": "0", "read_only": 1, "description": "Desactivado para la migración histórica actual. Los adjuntos nuevos siguen disponibles.", "insert_after": "cleanup_demo_after_migration"},
                {"fieldname": "last_migration_run", "label": "Última migración", "fieldtype": "Link", "options": "ConstruControl Migration Run", "read_only": 1, "insert_after": "evidence_bucket"},
                {"fieldname": "last_migration_at", "label": "Fecha de última migración", "fieldtype": "Datetime", "read_only": 1, "insert_after": "last_migration_run"},
            ],
            "CC User Access": [
                {"fieldname": "internal_user_id", "label": "Identificador interno original", "fieldtype": "Data", "read_only": 1, "insert_after": "email"},
                {"fieldname": "role_label", "label": "Rol visible", "fieldtype": "Data", "read_only": 1, "in_list_view": 1, "insert_after": "role_name"},
            ],
            "CC Audit Log": [
                {"fieldname": "actor_name", "label": "Nombre de la persona", "fieldtype": "Data", "read_only": 1, "in_list_view": 1, "insert_after": "actor"},
                {"fieldname": "actor_email", "label": "Correo", "fieldtype": "Data", "read_only": 1, "insert_after": "actor_name"},
                {"fieldname": "actor_role", "label": "Rol", "fieldtype": "Data", "read_only": 1, "in_list_view": 1, "insert_after": "actor_email"},
                {"fieldname": "actor_user_id", "label": "Identificador interno", "fieldtype": "Data", "read_only": 1, "insert_after": "actor_role"},
                {"fieldname": "actor_label", "label": "Identidad visible", "fieldtype": "Data", "read_only": 1, "insert_after": "actor_user_id"},
            ],
            "CC Immutable Audit Event": [
                {"fieldname": "actor_name", "label": "Nombre de la persona", "fieldtype": "Data", "read_only": 1, "insert_after": "description"},
                {"fieldname": "actor_email", "label": "Correo", "fieldtype": "Data", "read_only": 1, "insert_after": "actor_name"},
                {"fieldname": "actor_role", "label": "Rol", "fieldtype": "Data", "read_only": 1, "in_list_view": 1, "insert_after": "actor_email"},
                {"fieldname": "actor_user_id", "label": "Identificador interno", "fieldtype": "Data", "read_only": 1, "insert_after": "actor_role"},
                {"fieldname": "actor_label", "label": "Identidad visible", "fieldtype": "Data", "read_only": 1, "insert_after": "actor_user_id"},
            ],
        },
        update=True,
    )


def ensure_operational_integration() -> None:
    """Install or update ConstruControl without deleting ERPNext core or user data."""
    for definition in _doctype_definitions():
        _ensure_doctype(definition)
    _ensure_custom_fields()
    for definition in _load_json("assets.json")["pages"]:
        _ensure_page(definition)
    for definition in _load_json("assets.json")["reports"]:
        _ensure_report(definition)
    for definition in _load_json("assets.json")["print_formats"]:
        _ensure_print_format(definition)
    frappe.clear_cache()
