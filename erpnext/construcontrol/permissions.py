from __future__ import annotations

from typing import Any

import frappe

READ = {"read": 1}
READ_EXPORT = {"read": 1, "print": 1, "export": 1}
OPERATE = {"read": 1, "write": 1, "create": 1}
MANAGE = {"read": 1, "write": 1, "create": 1, "print": 1, "email": 1, "export": 1}
ADMIN = {"read": 1, "write": 1, "create": 1, "delete": 1, "print": 1, "email": 1, "export": 1, "share": 1}

# These records control access, automation, migration, notifications or immutable
# history and therefore require stricter rules than ordinary operational forms.
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
    "CC Generated Report": {
        "System Manager": ADMIN,
        "ConstruControl Manager": MANAGE,
        "ConstruControl Operator": {"read": 1, "create": 1, "print": 1},
        "ConstruControl Auditor": READ_EXPORT,
        "ConstruControl Viewer": READ,
    },
    "CC Notification Contact": {
        "System Manager": ADMIN,
        "ConstruControl Manager": MANAGE,
        "ConstruControl Operator": READ,
        "ConstruControl Auditor": READ_EXPORT,
    },
    "CC Notification Log": {
        "System Manager": ADMIN,
        "ConstruControl Manager": {"read": 1, "write": 1, "create": 1, "print": 1, "export": 1},
        "ConstruControl Operator": OPERATE,
        "ConstruControl Auditor": READ_EXPORT,
    },
    "CC Automation Rule": {
        "System Manager": ADMIN,
        "ConstruControl Manager": MANAGE,
        "ConstruControl Auditor": READ_EXPORT,
        "ConstruControl Operator": READ,
    },
    "CC Notification Rule": {
        "System Manager": ADMIN,
        "ConstruControl Manager": MANAGE,
        "ConstruControl Auditor": READ_EXPORT,
        "ConstruControl Operator": READ,
    },
    "CC Project Profile": {
        "System Manager": ADMIN,
        "ConstruControl Manager": MANAGE,
        "ConstruControl Auditor": READ_EXPORT,
        "ConstruControl Operator": READ,
        "ConstruControl Viewer": READ,
    },
}

_PERMISSION_FIELDS = (
    "read",
    "write",
    "create",
    "delete",
    "submit",
    "cancel",
    "amend",
    "report",
    "export",
    "import",
    "share",
    "print",
    "email",
)


def _permission_row(role: str, rights: dict[str, int]) -> dict[str, Any]:
    values: dict[str, Any] = {
        "role": role,
        "permlevel": 0,
        "if_owner": 0,
        "select": 0,
    }
    for right in _PERMISSION_FIELDS:
        values[right] = int(bool(rights.get(right)))
    return values


def _replace_custom_docperms(doctype: str, role_policy: dict[str, dict[str, int]]) -> None:
    """Apply runtime permissions without saving a standard DocType document.

    Frappe blocks saving app-owned (non-custom) DocType definitions when developer
    mode is disabled. Permission Manager itself stores production overrides in
    ``Custom DocPerm`` records, so use that supported runtime layer instead of
    mutating and exporting the standard DocType JSON during every migration.
    """
    frappe.db.delete("Custom DocPerm", {"parent": doctype})

    for idx, (role, rights) in enumerate(role_policy.items(), start=1):
        values = {
            "doctype": "Custom DocPerm",
            "parent": doctype,
            "idx": idx,
            **_permission_row(role, rights),
        }
        frappe.get_doc(values).insert(ignore_permissions=True)

    frappe.clear_cache(doctype=doctype)


def enforce_critical_permissions() -> None:
    """Replace stale runtime permission rows on security-sensitive DocTypes."""
    for doctype, role_policy in POLICIES.items():
        if not frappe.db.exists("DocType", doctype):
            continue
        _replace_custom_docperms(doctype, role_policy)
        print(f"[ConstruControl] critical permissions enforced: {doctype}", flush=True)
