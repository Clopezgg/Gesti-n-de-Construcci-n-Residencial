"""ConstruControl operational migration entry point.

The public import path remains stable while this wrapper applies the compatibility,
identity, concurrency and reconciliation rules required by the original
ConstruControl data.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

import frappe
from frappe.utils import getdate

from erpnext.construcontrol.migration import operational_importer as _operational
from erpnext.construcontrol.migration.native_records import ensure_item, ensure_supplier
from erpnext.construcontrol.migration.normalization import (
    ROLE_PRIORITY,
    build_actor_directory,
    normalize_movement_type,
    normalize_role,
    resolve_actor_identity,
)
from erpnext.construcontrol.migration.schema import (
    canonical_json,
    normalize_export_document,
    sanitize_payload,
    sha256_json,
    source_record_id,
    versioned_record_key,
)

ENTITY_DOCTYPES = _operational.ENTITY_DOCTYPES
validate_payload = _operational.validate_payload

if not hasattr(_operational, "_cc_original_values"):
    _operational._cc_original_values = _operational._values
if not hasattr(_operational, "_cc_original_upsert"):
    _operational._cc_original_upsert = _operational._upsert
_original_values = _operational._cc_original_values
_original_upsert = _operational._cc_original_upsert
_ACTOR_DIRECTORY: dict[str, dict[str, str]] = {}
_MIGRATION_LOCK_TIMEOUT_SECONDS = 5


def _migration_lock_name() -> str:
    site = str(getattr(frappe.local, "site", "") or "default")
    return f"construcontrol_migration_{site}"[:64]


@contextmanager
def _exclusive_migration_lock() -> Iterator[None]:
    """Serialize dry-runs and real imports on MariaDB.

    The lock is connection-scoped, survives transaction commits/rollbacks and is
    automatically released if the database connection closes. This protects the
    module-level compatibility handlers and prevents concurrent imports from
    creating competing records.
    """

    lock_name = _migration_lock_name()
    rows = frappe.db.sql(
        "SELECT GET_LOCK(%s, %s)",
        (lock_name, _MIGRATION_LOCK_TIMEOUT_SECONDS),
    )
    acquired = bool(rows and rows[0] and int(rows[0][0] or 0) == 1)
    if not acquired:
        frappe.throw(
            "Ya existe una validación o migración de ConstruControl en ejecución. "
            "Espere a que termine antes de iniciar otra."
        )

    try:
        yield
    finally:
        try:
            frappe.db.sql("SELECT RELEASE_LOCK(%s)", (lock_name,))
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                "ConstruControl migration lock release",
            )


def _build_actor_directory(payload: Any) -> dict[str, dict[str, str]]:
    projects = normalize_export_document(payload)
    return build_actor_directory(project.snapshot for project in projects)


def _source_datetime(value: Any) -> datetime | None:
    """Convert ISO-8601/Supabase timestamps to a MariaDB-safe UTC datetime."""
    if value in (None, ""):
        return None

    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip()
        if text.endswith(("Z", "z")):
            text = f"{text[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Fecha/hora de origen no válida: {str(value)[:120]}") from exc

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _normalize_temporal_values(doctype: str, values: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize every Date/Datetime field before Frappe sends values to MariaDB."""
    meta = frappe.get_meta(doctype)
    normalized = dict(values)
    for fieldname, value in tuple(normalized.items()):
        if value in (None, ""):
            continue
        field = meta.get_field(fieldname)
        if not field:
            continue
        if field.fieldtype == "Datetime":
            normalized[fieldname] = _source_datetime(value)
        elif field.fieldtype == "Date":
            try:
                normalized[fieldname] = getdate(str(value)[:10])
            except Exception as exc:
                raise ValueError(
                    f"Fecha de origen no válida para {doctype}.{fieldname}: {str(value)[:120]}"
                ) from exc
    return normalized


def _normalized_legacy(
    run: str,
    project_key: str,
    entity: str,
    index: int,
    record: Mapping[str, Any],
) -> tuple[Any, bool]:
    """Preserve the untouched source JSON while storing valid MariaDB datetimes."""
    sid = project_key if entity == "settings" else source_record_id(record, index)
    safe, _ = sanitize_payload(record)
    payload_hash = sha256_json(safe)
    key = versioned_record_key(project_key, entity, sid, payload_hash)
    if frappe.db.exists("ConstruControl Legacy Record", key):
        return frappe.get_doc("ConstruControl Legacy Record", key), False

    doc = frappe.get_doc(
        {
            "doctype": "ConstruControl Legacy Record",
            "record_key": key,
            "migration_run": run,
            "project_key": project_key,
            "entity_type": entity,
            "source_id": sid,
            "payload_hash": payload_hash,
            "migration_status": "Preserved",
            "source_created_at": _source_datetime(record.get("createdAt")),
            "source_updated_at": _source_datetime(record.get("updatedAt")),
            "is_deleted": _operational._deleted(record),
            "raw_payload": canonical_json(safe),
        }
    ).insert(ignore_permissions=True)
    return doc, True


def _normalized_upsert(doctype: str, key: str, values: dict[str, Any]) -> tuple[str, bool]:
    return _original_upsert(doctype, key, _normalize_temporal_values(doctype, values))


def _normalized_values(
    entity: str,
    record: Mapping[str, Any],
    source_id: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Normalize legacy values before Frappe validates fields."""
    values = _original_values(entity, record, source_id, context)

    if entity == "settings":
        values["address"] = record.get("projectAddress") or record.get("address")
        values["original_budget_hnl"] = (
            record.get("originalBudgetHnl") or record.get("totalBudgetHnl") or 0
        )
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
        values["movement_type"] = normalize_movement_type(
            record.get("type") or record.get("movementType")
        )
    elif entity == "userAccounts":
        role = normalize_role(record.get("role"))
        values["email"] = str(record.get("email") or "").strip().casefold()
        values["display_name"] = (
            record.get("name") or record.get("displayName") or record.get("email")
        )
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
    """Merge duplicate active identities without physically deleting history."""
    if not frappe.db.exists("DocType", "CC User Access"):
        return {
            "removed": 0,
            "merged": 0,
            "hard_deleted": 0,
            "remaining": 0,
        }

    rows = frappe.get_all(
        "CC User Access",
        fields=[
            "name",
            "email",
            "display_name",
            "role_name",
            "access_status",
            "is_logically_deleted",
        ],
        order_by="creation asc",
    )
    groups: dict[str, list[Any]] = defaultdict(list)
    for row in rows:
        email = str(row.email or "").strip().casefold()
        if email and not row.is_logically_deleted:
            groups[email].append(row)

    merged = 0
    for email, members in groups.items():
        if len(members) < 2:
            continue
        members.sort(
            key=lambda row: ROLE_PRIORITY.get(normalize_role(row.role_name), 0),
            reverse=True,
        )
        canonical = frappe.get_doc("CC User Access", members[0].name)
        best_role = normalize_role(members[0].role_name)
        canonical.email = email
        canonical.role_name = best_role
        if canonical.meta.has_field("role_label"):
            canonical.role_label = best_role
        if not canonical.display_name:
            canonical.display_name = next(
                (row.display_name for row in members if row.display_name),
                email,
            )
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
                    {
                        "target_name": canonical.name,
                        "created_by_migration": 0,
                    },
                    update_modified=False,
                )

            duplicate_doc = frappe.get_doc("CC User Access", duplicate.name)
            duplicate_doc.is_logically_deleted = 1
            duplicate_doc.save(ignore_permissions=True)
            merged += 1

    remaining = frappe.db.count(
        "CC User Access",
        {"is_logically_deleted": 0},
    )
    return {
        "removed": merged,
        "merged": merged,
        "hard_deleted": 0,
        "remaining": remaining,
    }


def _install_native_handlers() -> None:
    _operational._values = _normalized_values
    _operational._legacy = _normalized_legacy
    _operational._upsert = _normalized_upsert
    _operational._ensure_supplier = ensure_supplier
    _operational._ensure_item = ensure_item


def run_import(payload: Any, run_name: str, dry_run: bool = True) -> dict[str, Any]:
    global _ACTOR_DIRECTORY

    with _exclusive_migration_lock():
        _ACTOR_DIRECTORY = _build_actor_directory(payload)
        _install_native_handlers()
        previous_flag = getattr(frappe.flags, "in_construcontrol_migration", False)
        frappe.flags.in_construcontrol_migration = True
        try:
            result = _operational.run_import(
                payload,
                run_name,
                dry_run=dry_run,
            )
            if not dry_run:
                deduplication = _deduplicate_user_access(run_name)
                result["user_access_deduplication"] = deduplication
                result.setdefault("operational_unique_counts", {})[
                    "userAccounts"
                ] = deduplication["remaining"]
            return result
        finally:
            frappe.flags.in_construcontrol_migration = previous_flag
            _ACTOR_DIRECTORY = {}


_install_native_handlers()

__all__ = [
    "ENTITY_DOCTYPES",
    "normalize_role",
    "run_import",
    "validate_payload",
]
