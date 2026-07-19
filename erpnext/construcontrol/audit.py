from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

import frappe
from frappe.utils import now_datetime, today

_ROLE_LABELS = (
    ("System Manager", "ADMIN"),
    ("ConstruControl Manager", "MANAGER"),
    ("ConstruControl Operator", "OPERATOR"),
    ("ConstruControl Auditor", "AUDITOR"),
    ("ConstruControl Viewer", "VIEWER"),
)
_SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "passwordhash",
    "pin_hash",
    "pinhash",
    "access_token",
    "refresh_token",
    "api_secret",
    "secret",
    "service_role",
    "service_role_key",
}
_AUDIT_DOCTYPES = {"CC Audit Log", "CC Immutable Audit Event"}


def _role_label() -> str:
    roles = set(frappe.get_roles())
    for role, label in _ROLE_LABELS:
        if role in roles:
            return label
    return "USER"


def _display_name(user: str) -> str:
    if user == "Guest":
        return "Invitado"
    return str(frappe.db.get_value("User", user, "full_name") or user)


def _clean(value: Any) -> Any:
    if isinstance(value, list):
        return [_clean(item) for item in value]
    if not isinstance(value, Mapping):
        return value
    result: dict[str, Any] = {}
    for key, item in value.items():
        normalized = str(key).replace("-", "_").casefold()
        if normalized in _SENSITIVE_KEYS:
            continue
        if key in {"doctype", "__islocal", "__unsaved", "_comments", "_assign", "_liked_by"}:
            continue
        result[str(key)] = _clean(item)
    return result


def _snapshot(doc: Any) -> dict[str, Any]:
    try:
        return _clean(doc.as_dict())
    except Exception:
        return {"doctype": getattr(doc, "doctype", ""), "name": getattr(doc, "name", "")}


def _previous_snapshot(doc: Any) -> dict[str, Any]:
    previous = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
    return _snapshot(previous) if previous else {}


def _action(method: str | None) -> str:
    return {
        "after_insert": "CREATE",
        "on_update": "UPDATE",
        "on_submit": "SUBMIT",
        "on_cancel": "CANCEL",
        "on_trash": "DELETE",
    }.get(str(method or ""), str(method or "CHANGE").upper())


def record_event(doc: Any, method: str | None = None) -> None:
    """Write a role-aware audit event for every ConstruControl business record."""
    doctype = str(getattr(doc, "doctype", "") or "")
    if not doctype.startswith("CC ") or doctype in _AUDIT_DOCTYPES:
        return
    if getattr(frappe.flags, "in_construcontrol_migration", False):
        return
    if getattr(getattr(doc, "flags", None), "ignore_construcontrol_audit", False):
        return
    if getattr(frappe.flags, "in_construcontrol_recalculation", False):
        return
    if getattr(frappe.flags, "in_install", False) or getattr(frappe.flags, "in_migrate", False):
        return
    if method == "on_update" and getattr(getattr(doc, "flags", None), "in_insert", False):
        return

    action = _action(method)
    user = str(frappe.session.user or "Guest")
    display_name = _display_name(user)
    role = _role_label()
    previous = _previous_snapshot(doc)
    following = {} if action == "DELETE" else _snapshot(doc)
    if action == "UPDATE" and previous == following:
        return
    identity = f"{now_datetime().isoformat()}|{user}|{doctype}|{getattr(doc, 'name', '')}|{action}"
    source_key = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:40]

    values = {
        "doctype": "CC Audit Log",
        "source_key": source_key,
        "source_id": str(getattr(doc, "name", "") or source_key),
        "project": doc.get("project") if hasattr(doc, "get") else None,
        "code": source_key[:12].upper(),
        "title": f"{action} · {doctype} · {getattr(doc, 'name', '')}",
        "status": "recorded",
        "posting_date": today(),
        "description": f"{display_name} ejecutó {action} sobre {doctype}.",
        "actor": role,
        "actor_name": display_name,
        "actor_email": user,
        "actor_role": role,
        "actor_user_id": user,
        "actor_label": role,
        "action": action,
        "record_type": doctype,
        "record_id": str(getattr(doc, "name", "") or ""),
        "previous_state": json.dumps(previous, ensure_ascii=False, sort_keys=True, default=str),
        "next_state": json.dumps(following, ensure_ascii=False, sort_keys=True, default=str),
        "reason": None,
        "payload_json": json.dumps(
            {
                "actor": {"name": display_name, "email": user, "role": role, "user_id": user},
                "action": action,
                "record_type": doctype,
                "record_id": str(getattr(doc, "name", "") or ""),
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        "is_logically_deleted": 0,
    }
    frappe.get_doc(values).insert(ignore_permissions=True)
