from __future__ import annotations

from typing import Any

import frappe


_SPECIALIZATIONS: dict[str, dict[str, Any]] = {
    "CC User Access": {
        "title_field": "display_name",
        "search_fields": "display_name,email,role_name,access_status",
        "show_title_field_in_link": 1,
        "fields": {
            "source_id": {"hidden": 1, "in_list_view": 0},
            "project": {"hidden": 1, "in_list_view": 0},
            "code": {"hidden": 1, "in_list_view": 0},
            "title": {"hidden": 1, "in_list_view": 0},
            "status": {"hidden": 1, "in_list_view": 0},
            "posting_date": {"hidden": 1, "in_list_view": 0},
            "amount_hnl": {"hidden": 1, "in_list_view": 0},
            "description": {"hidden": 1, "in_list_view": 0},
            "email": {"label": "Correo histórico", "in_list_view": 1},
            "display_name": {"label": "Nombre", "in_list_view": 1},
            "role_name": {"label": "Rol histórico", "in_list_view": 1},
            "access_status": {"label": "Estado histórico", "in_list_view": 1},
        },
    },
    "CC Audit Log": {
        "title_field": "title",
        "search_fields": "title,actor_name,actor_email,action,record_type,record_id",
        "show_title_field_in_link": 1,
        "fields": {
            "source_id": {"hidden": 1, "in_list_view": 0},
            "project": {"hidden": 0, "in_list_view": 0},
            "code": {"hidden": 1, "in_list_view": 0},
            "status": {"hidden": 1, "in_list_view": 0},
            "amount_hnl": {"hidden": 1, "in_list_view": 0},
            "description": {"hidden": 0, "in_list_view": 0},
            "posting_date": {"label": "Fecha", "in_list_view": 1},
            "actor_name": {"label": "Usuario", "in_list_view": 1},
            "action": {"label": "Acción", "in_list_view": 1},
            "record_type": {"label": "Registro", "in_list_view": 1},
        },
    },
}


def specialize_operational_doctypes() -> None:
    """Apply canonical list/search metadata without deleting historical fields."""
    for doctype, specification in _SPECIALIZATIONS.items():
        if not frappe.db.exists("DocType", doctype):
            continue
        doc = frappe.get_doc("DocType", doctype)
        changed = False
        for fieldname in ("title_field", "search_fields", "show_title_field_in_link"):
            value = specification.get(fieldname)
            if doc.get(fieldname) != value:
                doc.set(fieldname, value)
                changed = True
        rows = {str(row.fieldname): row for row in doc.fields if row.fieldname}
        for fieldname, values in specification.get("fields", {}).items():
            row = rows.get(fieldname)
            if not row:
                continue
            for attribute, value in values.items():
                if row.get(attribute) != value:
                    row.set(attribute, value)
                    changed = True
        if changed:
            doc.save(ignore_permissions=True)
            frappe.clear_cache(doctype=doctype)


__all__ = ["specialize_operational_doctypes"]
