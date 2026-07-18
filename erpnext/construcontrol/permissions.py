from __future__ import annotations

from typing import Any

import frappe

READ = {"read": 1}
READ_EXPORT = {"read": 1, "print": 1, "export": 1}
MANAGE = {"read": 1, "write": 1, "create": 1, "print": 1, "email": 1, "export": 1}
ADMIN = {"read": 1, "write": 1, "create": 1, "delete": 1, "print": 1, "email": 1, "export": 1, "share": 1}

# These records control access, automation, migration or immutable history and
# therefore require stricter rules than ordinary operational forms.
POLICIES: dict[str, dict[str, dict[str, int]]] = {
    "ConstruControl Settings": {
        "System Manager": ADMIN,
        "ConstruControl Manager": {"read": 1, "write": 1},
        "ConstruControl Auditor": READ,
    },
    "ConstruControl Migration Run": {
        "System Manager": ADMIN,
        "ConstruControl Manager": READ_EXPORT,
        "ConstruControl Auditor": READ_EXPORT,
    },
    "ConstruControl Legacy Record": {
        "System Manager": {"read": 1, "write": 1, "create": 1, "print": 1, "export": 1},
        "ConstruControl Manager": READ_EXPORT,
        "ConstruControl Auditor": READ_EXPORT,
    },
    "ConstruControl Migration Reconciliation": {
        "System Manager": {"read": 1, "write": 1, "create": 1, "print": 1, "export": 1},
        "ConstruControl Manager": READ_EXPORT,
        "ConstruControl Auditor": READ_EXPORT,
    },
    "CC User Access": {
        "System Manager": ADMIN,
        "ConstruControl Manager": READ_EXPORT,
        "ConstruControl Auditor": READ_EXPORT,
    },
    "CC Audit Log": {
        "System Manager": READ_EXPORT,
        "ConstruControl Manager": READ_EXPORT,
        "ConstruControl Auditor": READ_EXPORT,
        "ConstruControl Operator": READ,
        "ConstruControl Viewer": READ,
    },
    "CC Immutable Audit Event": {
        "System Manager": READ_EXPORT,
        "ConstruControl Manager": READ_EXPORT,
        "ConstruControl Auditor": READ_EXPORT,
        "ConstruControl Operator": READ,
        "ConstruControl Viewer": READ,
    },
    "CC Backup Snapshot": {
        "System Manager": READ_EXPORT,
        "ConstruControl Manager": READ_EXPORT,
        "ConstruControl Auditor": READ_EXPORT,
    },
    "CC Automation Execution": {
        "System Manager": READ_EXPORT,
        "ConstruControl Manager": READ_EXPORT,
        "ConstruControl Auditor": READ_EXPORT,
    },
    "CC Notification Log": {
        "System Manager": READ_EXPORT,
        "ConstruControl Manager": READ_EXPORT,
        "ConstruControl Auditor": READ_EXPORT,
    },
    "CC Automation Rule": {
        "System Manager": ADMIN,
        "ConstruControl Manager": MANAGE,
        "ConstruControl Auditor": READ_EXPORT,
        "ConstruControl Operator": READ,
        "ConstruControl Viewer": READ,
    },
    "CC Notification Rule": {
        "System Manager": ADMIN,
        "ConstruControl Manager": MANAGE,
        "ConstruControl Auditor": READ_EXPORT,
        "ConstruControl Operator": READ,
        "ConstruControl Viewer": READ,
    },
    "CC Project Profile": {
        "System Manager": ADMIN,
        "ConstruControl Manager": MANAGE,
        "ConstruControl Auditor": READ_EXPORT,
        "ConstruControl Operator": READ,
        "ConstruControl Viewer": READ,
    },
}


def _permission_row(role: str, rights: dict[str, int]) -> dict[str, Any]:
    values: dict[str, Any] = {"role": role, "permlevel": 0}
    for right in ("read", "write", "create", "delete", "submit", "cancel", "amend", "report", "export", "import", "share", "print", "email"):
        values[right] = int(bool(rights.get(right)))
    return values


def enforce_critical_permissions() -> None:
    """Replace stale permission rows on security-sensitive ConstruControl DocTypes."""
    for doctype, role_policy in POLICIES.items():
        if not frappe.db.exists("DocType", doctype):
            continue
        document = frappe.get_doc("DocType", doctype)
        document.set("permissions", [])
        for role, rights in role_policy.items():
            document.append("permissions", _permission_row(role, rights))
        document.save(ignore_permissions=True)
        frappe.clear_cache(doctype=doctype)
