from __future__ import annotations

from typing import Any

import frappe
from frappe import _

_READER_ROLES = {
    "System Manager",
    "ConstruControl Manager",
    "ConstruControl Operator",
    "ConstruControl Auditor",
    "ConstruControl Viewer",
}
_WRITER_ROLES = {
    "System Manager",
    "ConstruControl Manager",
    "ConstruControl Operator",
}
_MANAGER_ROLES = {"System Manager", "ConstruControl Manager"}
_GLOBAL_PROJECT_ROLES = {"System Manager", "ConstruControl Manager"}


def current_roles() -> set[str]:
    return set(frappe.get_roles())


def require_construcontrol_access(*, write: bool = False, manage: bool = False) -> set[str]:
    roles = current_roles()
    required = _MANAGER_ROLES if manage else _WRITER_ROLES if write else _READER_ROLES
    if not (roles & required):
        frappe.throw(_("No tiene permisos para esta operación de ConstruControl."), frappe.PermissionError)
    return roles


def has_global_project_access(roles: set[str] | None = None) -> bool:
    return bool((roles or current_roles()) & _GLOBAL_PROJECT_ROLES)


def allowed_project_names(user: str | None = None, roles: set[str] | None = None) -> list[str] | None:
    """Return None for unrestricted managers, otherwise the exact Project permission list."""
    roles = roles or current_roles()
    if has_global_project_access(roles):
        return None
    user = str(user or frappe.session.user or "").strip()
    if not user or user == "Guest":
        return []
    return sorted(
        {
            str(value)
            for value in frappe.get_all(
                "User Permission",
                filters={"user": user, "allow": "Project"},
                pluck="for_value",
            )
            if value
        }
    )


def assert_project_access(project: str, *, write: bool = False) -> str:
    require_construcontrol_access(write=write)
    project = str(project or "").strip()
    if not project or not frappe.db.exists("Project", project):
        frappe.throw(_("El proyecto seleccionado no existe."))
    allowed = allowed_project_names()
    if allowed is not None and project not in allowed:
        frappe.throw(_("No tiene permiso para consultar este proyecto."), frappe.PermissionError)
    return project


def project_filter(project: str | None = None) -> dict[str, Any]:
    """Build a server-side filter that cannot escape the current user's project scope."""
    require_construcontrol_access()
    if project:
        return {"project": assert_project_access(project)}
    allowed = allowed_project_names()
    if allowed is None:
        return {}
    if not allowed:
        return {"project": "__construcontrol_no_project_access__"}
    return {"project": ["in", allowed]}


def validation_bypass_active() -> bool:
    """Allow only schema installation and the authorized historical migration path."""
    flags = getattr(frappe, "flags", None)
    return bool(
        getattr(flags, "in_construcontrol_migration", False)
        or getattr(flags, "in_install", False)
        or getattr(flags, "in_migrate", False)
    )


def validate_document_project_access(
    doc: Any,
    method: str | None = None,
    *,
    write: bool = True,
) -> None:
    """Apply the same project boundary to Desk, REST and custom document writes."""
    if validation_bypass_active():
        return
    meta = getattr(doc, "meta", None)
    if not meta or not meta.has_field("project"):
        return
    project = str(doc.get("project") or "").strip()
    if not project:
        frappe.throw(_("Seleccione un proyecto."))
    assert_project_access(project, write=write)


def accessible_project_profiles() -> list[dict[str, Any]]:
    filters: dict[str, Any] = {"is_logically_deleted": 0}
    filters.update(project_filter())
    return frappe.get_all(
        "CC Project Profile",
        filters=filters,
        fields=["project", "project_name", "is_current"],
        order_by="is_current desc, modified desc",
    )


def resolve_accessible_project(project: str | None = None) -> str | None:
    if project:
        return assert_project_access(project)
    profiles = accessible_project_profiles()
    return str(profiles[0].get("project")) if profiles else None


__all__ = [
    "accessible_project_profiles",
    "allowed_project_names",
    "assert_project_access",
    "current_roles",
    "has_global_project_access",
    "project_filter",
    "require_construcontrol_access",
    "resolve_accessible_project",
    "validate_document_project_access",
    "validation_bypass_active",
]
