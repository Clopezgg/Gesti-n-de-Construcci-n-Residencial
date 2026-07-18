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
from erpnext.construcontrol.migration.schema import normalize_export_document

ENTITY_DOCTYPES = _operational.ENTITY_DOCTYPES
validate_payload = _operational.validate_payload

if not hasattr(_operational, "_cc_original_values"):
    _operational._cc_original_values = _operational._values
_original_values = _operational._cc_original_values

_ROLE_ALIASES = {
    "admin": "ADMIN",
    "administrator": "ADMIN",
    "system manager": "ADMIN",
    "construcontrol manager": "MANAGER",
    "manager": "MANAGER",
    "gestor": "MANAGER",
    "operator": "OPERATOR",
    "operador": "OPERATOR",
    "construcontrol operator": "OPERATOR",
    "auditor": "AUDITOR",
    "construcontrol auditor": "AUDITOR",
    "viewer": "VIEWER",
    "visualizador": "VIEWER",
    "construcontrol viewer": "VIEWER",
}
_ROLE_PRIORITY = {"ADMIN": 50, "MANAGER": 40, "OPERATOR": 30, "AUDITOR": 20, "VIEWER": 10, "USER": 0}
_ACTOR_DIRECTORY: dict[str, dict[str, str]] = {}


def normalize_role(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "USER"
    return _ROLE_ALIASES.get(text.casefold(), text.upper().replace(" ", "_"))


def _directory_keys(record: Mapping[str, Any]) -> list[str]:
    values = (record.get("id"), record.get("userId"), record.get("email"), record.get("providerId"))
    return [str(value).strip().casefold() for value in values if value]


def _build_actor_directory(payload: Any) -> dict[str, dict[str, str]]:
    directory: dict[str, dict[str, str]] = {}
    for project in normalize_export_document(payload):
        accounts = project.snapshot.get("userAccounts")
        if not isinstance(accounts, list):
            continue
        for record in accounts:
            if not isinstance(record, Mapping):
                continue
            role = normalize_role(record.get("role"))
            identity = {
                "user_id": str(record.get("id") or record.get("userId") or ""),
                "email": str(record.get("email") or ""),
                "display_name": str(record.get("name") or record.get("displayName") or record.get("email") or ""),
                "role": role,
            }
            for key in _directory_keys(record):
                current = directory.get(key)
                if current is None or _ROLE_PRIORITY.get(role, 0) > _ROLE_PRIORITY.get(current.get("role", "USER"), 0):
                    directory[key] = identity
    return directory


def _actor_identity(record: Mapping[str, Any]) -> dict[str, str]:
    actor = str(record.get("actor") or record.get("createdBy") or record.get("userId") or "").strip()
    identity = _ACTOR_DIRECTORY.get(actor.casefold()) if actor else None
    if identity:
        return identity
    email = actor if "@" in actor else str(record.get("email") or "")
    role = normalize_role(record.get("actorRole") or record.get("role"))
    display_name = str(record.get("actorName") or record.get("displayName") or record.get("name") or email or actor)
    return {
        "user_id": str(record.get("actorUserId") or record.get("userId") or actor),
        "email": email,
        "display_name": display_name,
        "role": role,
    }


def _normalize_movement_type(value: Any) -> str:
    text = str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")
    incoming = {"entry", "purchase", "receipt", "receive", "adjustment_in", "return_in", "initial"}
    outgoing = {"consumption", "consume", "use", "issue", "exit", "adjustment_out", "return_out"}
    if text in incoming:
        return "adjustment_in"
    if text in outgoing:
        return "consumption" if text in {"consumption", "consume", "use", "issue", "exit"} else "adjustment_out"
    return "consumption"


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
        values["movement_type"] = _normalize_movement_type(record.get("type") or record.get("movementType"))
    elif entity == "userAccounts":
        role = normalize_role(record.get("role"))
        values["email"] = str(record.get("email") or "").strip().casefold()
        values["display_name"] = record.get("name") or record.get("displayName") or record.get("email")
        values["role_name"] = role
        values["role_label"] = role
        values["internal_user_id"] = record.get("id") or record.get("userId")
        values["access_status"] = record.get("status") or "active"
    elif entity in {"auditLogs", "enterprisePlatform.immutableAudit"}:
        identity = _actor_identity(record)
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
        members.sort(key=lambda row: _ROLE_PRIORITY.get(normalize_role(row.role_name), 0), reverse=True)
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
                filters={
                    "migration_run": run_name,
                    "target_doctype": "CC User Access",
                    "target_name": duplicate.name,
                },
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


def run_import(payload: Any, run_name: str, dry_run: bool = True) -> dict[str, Any]:
    global _ACTOR_DIRECTORY
    _ACTOR_DIRECTORY = _build_actor_directory(payload)
    _operational._values = _normalized_values
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


_operational._values = _normalized_values

__all__ = ["ENTITY_DOCTYPES", "normalize_role", "run_import", "validate_payload"]
