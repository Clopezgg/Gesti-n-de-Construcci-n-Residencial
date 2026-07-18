"""ConstruControl operational migration entry point.

The public import path remains stable while this wrapper applies the compatibility,
identity and reconciliation rules required by the original ConstruControl data.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from typing import Any

import frappe

from erpnext.construcontrol.migration import operational_importer as _operational
from erpnext.construcontrol.migration.native_records import ensure_item, ensure_supplier
from erpnext.construcontrol.migration.normalization import (
    ROLE_PRIORITY,
    build_actor_directory,
    normalize_movement_type,
    normalize_role,
    resolve_actor_identity,
)
from erpnext.construcontrol.migration.schema import normalize_export_document

ENTITY_DOCTYPES = _operational.ENTITY_DOCTYPES
validate_payload = _operational.validate_payload

if not hasattr(_operational, "_cc_original_values"):
    _operational._cc_original_values = _operational._values
_original_values = _operational._cc_original_values
_ACTOR_DIRECTORY: dict[str, dict[str, str]] = {}


def _build_actor_directory(payload: Any) -> dict[str, dict[str, str]]:
    projects = normalize_export_document(payload)
    return build_actor_directory(project.snapshot for project in projects)


def _normalized_values(entity: str, record: Mapping[str, Any], source_id: str, context: dict[str, Any]) -> dict[str, Any]:
    """Normalize legacy values before Frappe validates fields."""
    values = _original_values(entity, record, source_id, context)

    if entity == "settings":
        values["address"] = record.get("projectAddress") or record.get("address")
        values["original_budget_hnl"] = record.get("originalBudgetHnl") or record.get("totalBudgetHnl") or 0
    elif entity == "expenses":
        if values.get("financial_status") not in {"pending", "paid", "cancelled", "reimbursed"}:
            values["financial_status"] = "pending" if record.get("status") == "pending" else "paid"
        if not record.get("commercialSource") and not record.get("source"):
            values["commercial_source"] = {
                "labor": "MANO DE OBRA",
                "materials": "FERRETERÍA / MATERIALES",
                "transport": "FLETE O TRANSPORTE",
                "machinery": "MAQUINARIA",
                "service": "SERVICIO",
                "permit": "PERMISO",
            }.get(str(record.get("category")), str(record.get("category") or "OTRO").upper())
    elif entity == "inventoryMovements":
        values["movement_type"] = normalize_movement_type(record.get("type") or record.get("movementType"))
    elif entity == "userAccounts":
        role = normalize_role(record.get("role"))
        values["email"] = str(record.get("email") or "").strip().casefold()
        values["display_name"] = record.get("name") or record.get("displayName") or record.get("email")
        values["role_name"] = role
        values["role_label"] = role
        values["internal_user_id"] = record.get("id") or record.get("userId")
        values["access_status"] = record.get("status") or "active"
    elif entity in {"auditLogs", "enterprisePlatform.immutableAudit"}:
        identity = resolve_actor_identity(record, _ACTOR_DIRECTORY)
        values["actor"] = identity["role"]
        values["actor_email"] = identity["email"]
        values["actor_name"] = identity["display_name"]
        values["actor_role"] = identity["role"]
        values["actor_user_id"] = identity["user_id"]
        values["actor_label"] = identity["role"]
    return values


def _deduplicate_user_access(run_name: str) -> dict[str, int]:
    if not frappe.db.exists("DocType", "CC User Access"):
        return {"removed": 0, "remaining": 0}

    rows = frappe.get_all(
        "CC User Access",
        fields=["name", "email", "display_name", "role_name", "access_status", "is_logically_deleted"],
        order_by="creation asc",
    )
    groups: dict[str, list[Any]] = defaultdict(list)
    for row in rows:
        email = str(row.email or "").strip().casefold()
        if email and not row.is_logically_deleted:
            groups[email].append(row)

    removed = 0
    for email, members in groups.items():
        if len(members) < 2:
            continue
        members.sort(key=lambda row: ROLE_PRIORITY.get(normalize_role(row.role_name), 0), reverse=True)
        canonical = frappe.get_doc("CC User Access", members[0].name)
        best_role = normalize_role(members[0].role_name)
        canonical.email = email
        canonical.role_name = best_role
        if canonical.meta.has_field("role_label"):
            canonical.role_label = best_role
        if not canonical.display_name:
            canonical.display_name = next((row.display_name for row in members if row.display_name), email)
        canonical.save(ignore_permissions=True)

        for duplicate in members[1:]:
            legacy_names = frappe.get_all(
                "ConstruControl Legacy Record",
                filters={"migration_run": run_name, "target_doctype": "CC User Access", "target_name": duplicate.name},
                pluck="name",
            )
            for legacy_name in legacy_names:
                frappe.db.set_value(
                    "ConstruControl Legacy Record",
                    legacy_name,
                    {"target_name": canonical.name, "created_by_migration": 0},
                    update_modified=False,
                )
            frappe.delete_doc("CC User Access", duplicate.name, ignore_permissions=True, force=True)
            removed += 1

    remaining = frappe.db.count("CC User Access", {"is_logically_deleted": 0})
    return {"removed": removed, "remaining": remaining}


def _install_native_handlers() -> None:
    _operational._values = _normalized_values
    _operational._ensure_supplier = ensure_supplier
    _operational._ensure_item = ensure_item


def run_import(payload: Any, run_name: str, dry_run: bool = True) -> dict[str, Any]:
    global _ACTOR_DIRECTORY
    _ACTOR_DIRECTORY = _build_actor_directory(payload)
    _install_native_handlers()
    previous_flag = getattr(frappe.flags, "in_construcontrol_migration", False)
    frappe.flags.in_construcontrol_migration = True
    try:
        result = _operational.run_import(payload, run_name, dry_run=dry_run)
        if not dry_run:
            deduplication = _deduplicate_user_access(run_name)
            result["user_access_deduplication"] = deduplication
            result.setdefault("operational_unique_counts", {})["userAccounts"] = deduplication["remaining"]
        return result
    finally:
        frappe.flags.in_construcontrol_migration = previous_flag
        _ACTOR_DIRECTORY = {}


_install_native_handlers()

__all__ = ["ENTITY_DOCTYPES", "normalize_role", "run_import", "validate_payload"]
