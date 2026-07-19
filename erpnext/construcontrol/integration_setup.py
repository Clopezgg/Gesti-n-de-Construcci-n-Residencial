from __future__ import annotations

import json
from typing import Any

import frappe

_BASE_INTEGRATIONS: tuple[dict[str, Any], ...] = (
    {
        "integration_code": "ERPNEXT_CORE",
        "integration_name": "Motor ERPNext",
        "category": "core",
        "provider_type": "erpnext_core",
        "description": "Motor interno de documentos, permisos, contabilidad y procesos de ConstruControl.",
        "brand_color": "#175C4C",
        "auth_mode": "managed",
        "enabled": 1,
        "status": "healthy",
        "is_protected": 1,
        "sort_order": 10,
    },
    {
        "integration_code": "SUPABASE_MIGRATION",
        "integration_name": "Importación histórica Supabase",
        "category": "data",
        "provider_type": "supabase",
        "description": "Origen histórico utilizado por la migración segura. No controla la base productiva de ERPNext.",
        "brand_color": "#3ECF8E",
        "auth_mode": "managed",
        "enabled": 0,
        "status": "disabled",
        "is_protected": 1,
        "sort_order": 20,
    },
    {
        "integration_code": "EMAIL_NOTIFICATIONS",
        "integration_name": "Correo y notificaciones",
        "category": "communication",
        "provider_type": "email",
        "description": "Envío de avisos y documentos mediante las cuentas de correo configuradas en Frappe.",
        "brand_color": "#3B6EA8",
        "auth_mode": "managed",
        "enabled": 0,
        "status": "draft",
        "is_protected": 1,
        "sort_order": 30,
    },
)


def seed_integration_registry() -> None:
    if not frappe.db.exists("DocType", "CC Integration Registry"):
        return
    for values in _BASE_INTEGRATIONS:
        code = str(values["integration_code"])
        existing = frappe.db.get_value("CC Integration Registry", {"integration_code": code}, "name")
        doc = frappe.get_doc("CC Integration Registry", existing) if existing else frappe.new_doc("CC Integration Registry")
        doc.integration_code = code
        doc.source_key = f"integration:{code.casefold()}"
        doc.source_id = code
        for fieldname, value in values.items():
            doc.set(fieldname, value)
        doc.is_logically_deleted = 0
        doc.payload_json = json.dumps({"seed": "ConstruControl", "integration_code": code}, sort_keys=True)
        if doc.is_new():
            doc.insert(ignore_permissions=True)
        else:
            # Never overwrite an administrator's enabled/status choice after first installation.
            for fieldname in ("integration_name", "category", "provider_type", "description", "brand_color", "auth_mode", "is_protected", "sort_order"):
                doc.set(fieldname, values[fieldname])
            doc.save(ignore_permissions=True)
    frappe.clear_cache(doctype="CC Integration Registry")


__all__ = ["seed_integration_registry"]
