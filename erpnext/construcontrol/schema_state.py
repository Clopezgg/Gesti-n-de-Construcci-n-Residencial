from __future__ import annotations

from typing import Any

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import now_datetime


def ensure_schema_state_fields() -> None:
    """Install read-only metadata that identifies the active data contract."""
    create_custom_fields(
        {
            "ConstruControl Settings": [
                {
                    "fieldname": "runtime_contract_section",
                    "label": "Contrato de datos instalado",
                    "fieldtype": "Section Break",
                },
                {
                    "fieldname": "runtime_contract_version",
                    "label": "Versión del contrato",
                    "fieldtype": "Int",
                    "read_only": 1,
                },
                {
                    "fieldname": "runtime_contract_sha256",
                    "label": "Huella SHA-256 del contrato",
                    "fieldtype": "Data",
                    "read_only": 1,
                },
                {
                    "fieldname": "runtime_contract_validated_at",
                    "label": "Última validación del contrato",
                    "fieldtype": "Datetime",
                    "read_only": 1,
                },
                {
                    "fieldname": "runtime_contract_doctype_count",
                    "label": "DocTypes incluidos",
                    "fieldtype": "Int",
                    "read_only": 1,
                },
                {
                    "fieldname": "runtime_contract_asset_count",
                    "label": "Activos incluidos",
                    "fieldtype": "Int",
                    "read_only": 1,
                },
            ]
        },
        update=True,
    )


def record_runtime_contract(report: dict[str, Any]) -> None:
    """Persist the exact validated contract only after schema installation succeeds."""
    if not report.get("ok"):
        raise RuntimeError("No se puede registrar un contrato runtime no validado.")

    ensure_schema_state_fields()
    settings = frappe.get_single("ConstruControl Settings")
    values = {
        "runtime_contract_version": report.get("contract_version"),
        "runtime_contract_sha256": report.get("sha256"),
        "runtime_contract_validated_at": now_datetime(),
        "runtime_contract_doctype_count": report.get("doctype_count"),
        "runtime_contract_asset_count": report.get("asset_count"),
    }
    changed = False
    for fieldname, value in values.items():
        if settings.meta.has_field(fieldname) and settings.get(fieldname) != value:
            settings.set(fieldname, value)
            changed = True

    if changed:
        settings.save(ignore_permissions=True)
    print(
        "[ConstruControl] runtime contract state recorded "
        f"v{report.get('contract_version')} sha256={str(report.get('sha256') or '')[:16]}",
        flush=True,
    )


__all__ = ["ensure_schema_state_fields", "record_runtime_contract"]
