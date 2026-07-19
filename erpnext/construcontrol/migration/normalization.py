from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

ROLE_ALIASES = {
    "admin": "admin",
    "administrator": "admin",
    "system manager": "admin",
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
ROLE_PRIORITY = {"admin": 50, "ADMIN": 50, "MANAGER": 40, "OPERATOR": 30, "AUDITOR": 20, "VIEWER": 10, "USER": 0}


def normalize_role(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "USER"
    return ROLE_ALIASES.get(text.casefold(), text.upper().replace(" ", "_"))


def normalize_movement_type(value: Any) -> str:
    text = str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")
    incoming = {"entry", "purchase", "receipt", "receive", "adjustment_in", "return_in", "initial"}
    outgoing = {"consumption", "consume", "use", "issue", "exit", "adjustment_out", "return_out"}
    if text in incoming:
        return "adjustment_in"
    if text in outgoing:
        return "consumption" if text in {"consumption", "consume", "use", "issue", "exit"} else "adjustment_out"
    return "consumption"


def _directory_keys(record: Mapping[str, Any]) -> list[str]:
    values = (record.get("id"), record.get("userId"), record.get("email"), record.get("providerId"))
    return [str(value).strip().casefold() for value in values if value]


def build_actor_directory(snapshots: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, str]]:
    directory: dict[str, dict[str, str]] = {}
    for snapshot in snapshots:
        accounts = snapshot.get("userAccounts")
        if not isinstance(accounts, list):
            continue
        for record in accounts:
            if not isinstance(record, Mapping):
                continue
            role = normalize_role(record.get("role"))
            identity = {
                "user_id": str(record.get("id") or record.get("userId") or ""),
                "email": str(record.get("email") or "").strip().casefold(),
                "display_name": str(record.get("name") or record.get("displayName") or record.get("email") or ""),
                "role": role,
            }
            for key in _directory_keys(record):
                current = directory.get(key)
                if current is None or ROLE_PRIORITY.get(role, 0) > ROLE_PRIORITY.get(current.get("role", "USER"), 0):
                    directory[key] = identity
    return directory


def resolve_actor_identity(record: Mapping[str, Any], directory: Mapping[str, Mapping[str, str]]) -> dict[str, str]:
    actor = str(record.get("actor") or record.get("createdBy") or record.get("userId") or "").strip()
    identity = directory.get(actor.casefold()) if actor else None
    if identity:
        return dict(identity)
    email = actor.casefold() if "@" in actor else str(record.get("email") or "").strip().casefold()
    role = normalize_role(record.get("actorRole") or record.get("role"))
    display_name = str(record.get("actorName") or record.get("displayName") or record.get("name") or email or actor)
    return {
        "user_id": str(record.get("actorUserId") or record.get("userId") or actor),
        "email": email,
        "display_name": display_name,
        "role": role,
    }
