from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, validate_email_address

_MANAGEMENT_ROLES = {"System Manager", "ConstruControl Manager"}
_BUSINESS_ROLES = (
    "ConstruControl Manager",
    "ConstruControl Operator",
    "ConstruControl Auditor",
    "ConstruControl Viewer",
)
_ROLE_LABELS = {
    "System Manager": "ADMIN",
    "ConstruControl Manager": "MANAGER",
    "ConstruControl Operator": "OPERATOR",
    "ConstruControl Auditor": "AUDITOR",
    "ConstruControl Viewer": "VIEWER",
}


def _require_management() -> None:
    if not (_MANAGEMENT_ROLES & set(frappe.get_roles())):
        frappe.throw(_("No tiene permisos para administrar usuarios."), frappe.PermissionError)


def _can_assign_system_manager() -> bool:
    return "System Manager" in set(frappe.get_roles())


def _visible_role(roles: set[str]) -> str:
    for role in ("System Manager", *_BUSINESS_ROLES):
        if role in roles:
            return _ROLE_LABELS[role]
    return "USER"


def _role_from_label(label: str) -> str:
    normalized = str(label or "").strip().upper()
    reverse = {value: key for key, value in _ROLE_LABELS.items()}
    role = reverse.get(normalized)
    if not role:
        frappe.throw(_("Seleccione un rol válido."))
    if role == "System Manager" and not _can_assign_system_manager():
        frappe.throw(_("Solo un administrador del sistema puede asignar el rol ADMIN."), frappe.PermissionError)
    return role


def _project_permissions(users: list[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    if not users:
        return result
    for row in frappe.get_all(
        "User Permission",
        filters={"user": ["in", users], "allow": "Project"},
        fields=["user", "for_value", "is_default"],
        order_by="is_default desc, creation asc",
    ):
        if row.get("for_value"):
            result[str(row.get("user"))].append(str(row.get("for_value")))
    return result


def _user_roles(users: list[str]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    if not users:
        return result
    allowed = ["System Manager", *_BUSINESS_ROLES]
    for row in frappe.get_all(
        "Has Role",
        filters={"parent": ["in", users], "role": ["in", allowed]},
        fields=["parent", "role"],
    ):
        result[str(row.get("parent"))].add(str(row.get("role")))
    return result


def _legacy_access(users: list[str]) -> dict[str, dict[str, Any]]:
    if not users or not frappe.db.exists("DocType", "CC User Access"):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for row in frappe.get_all(
        "CC User Access",
        filters={"email": ["in", users], "is_logically_deleted": 0},
        fields=["email", "source_id", "provider", "access_status", "role_name"],
        order_by="modified desc",
    ):
        email = str(row.get("email") or "")
        if email and email not in result:
            result[email] = dict(row)
    return result


@frappe.whitelist()
def get_user_center(search: str = "", enabled: str | int | None = None) -> dict[str, Any]:
    _require_management()
    filters: dict[str, Any] = {"user_type": "System User", "name": ["not in", ["Guest"]]}
    if enabled not in (None, ""):
        filters["enabled"] = cint(enabled)
    or_filters: dict[str, Any] | None = None
    search = str(search or "").strip()
    if search:
        like = f"%{search}%"
        or_filters = {"name": ["like", like], "full_name": ["like", like], "email": ["like", like]}

    rows = frappe.get_all(
        "User",
        filters=filters,
        or_filters=or_filters,
        fields=["name", "email", "full_name", "first_name", "last_name", "enabled", "last_login", "last_active", "user_image", "creation", "modified"],
        order_by="enabled desc, full_name asc, name asc",
        limit_page_length=500,
    )
    names = [str(row.get("name")) for row in rows]
    roles = _user_roles(names)
    projects = _project_permissions(names)
    legacy = _legacy_access(names)

    users = []
    for row in rows:
        user_id = str(row.get("name"))
        role_set = roles.get(user_id, set())
        historical = legacy.get(user_id) or {}
        users.append(
            {
                "user_id": user_id,
                "email": row.get("email") or user_id,
                "display_name": row.get("full_name") or user_id,
                "first_name": row.get("first_name") or "",
                "last_name": row.get("last_name") or "",
                "enabled": cint(row.get("enabled")),
                "role": _visible_role(role_set),
                "roles": sorted(role_set),
                "projects": projects.get(user_id, []),
                "last_login": row.get("last_login"),
                "last_active": row.get("last_active"),
                "user_image": row.get("user_image") or "",
                "protected": user_id in {"Administrator", frappe.session.user},
                "historical_source_id": historical.get("source_id"),
                "historical_provider": historical.get("provider"),
                "historical_status": historical.get("access_status"),
            }
        )

    return {
        "users": users,
        "projects": frappe.get_all("Project", filters={"is_active": "Yes"}, fields=["name", "project_name"], order_by="project_name asc"),
        "roles": ["ADMIN", "MANAGER", "OPERATOR", "AUDITOR", "VIEWER"],
        "can_assign_admin": _can_assign_system_manager(),
    }


def _set_business_role(doc: Any, role: str) -> None:
    existing = [row for row in doc.roles if row.role not in {*_BUSINESS_ROLES, "System Manager"}]
    doc.set("roles", [])
    for row in existing:
        doc.append("roles", {"role": row.role})
    doc.append("roles", {"role": role})


def _set_project_permission(user: str, project: str) -> None:
    current = frappe.get_all("User Permission", filters={"user": user, "allow": "Project"}, pluck="name")
    for name in current:
        frappe.delete_doc("User Permission", name, ignore_permissions=True, force=True)
    if project:
        frappe.get_doc(
            {
                "doctype": "User Permission",
                "user": user,
                "allow": "Project",
                "for_value": project,
                "is_default": 1,
                "apply_to_all_doctypes": 1,
            }
        ).insert(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def save_user(
    email: str,
    first_name: str,
    last_name: str = "",
    role: str = "VIEWER",
    project: str = "",
    enabled: int | str = 1,
) -> dict[str, Any]:
    _require_management()
    email = str(email or "").strip().lower()
    first_name = str(first_name or "").strip()
    last_name = str(last_name or "").strip()
    project = str(project or "").strip()
    if not email or not validate_email_address(email, throw=False):
        frappe.throw(_("Ingrese un correo electrónico válido."))
    if not first_name:
        frappe.throw(_("El nombre es obligatorio."))
    if len(first_name) > 140 or len(last_name) > 140:
        frappe.throw(_("El nombre supera la longitud permitida."))
    internal_role = _role_from_label(role)
    if project and not frappe.db.exists("Project", project):
        frappe.throw(_("El proyecto seleccionado no existe."))

    exists = bool(frappe.db.exists("User", email))
    if exists:
        doc = frappe.get_doc("User", email)
    else:
        doc = frappe.new_doc("User")
        doc.email = email
        doc.user_type = "System User"
        doc.send_welcome_email = 0
    if doc.name == "Administrator" and not _can_assign_system_manager():
        frappe.throw(_("No puede modificar la cuenta Administrator."), frappe.PermissionError)
    doc.first_name = first_name
    doc.last_name = last_name
    doc.enabled = cint(enabled)
    _set_business_role(doc, internal_role)
    if exists:
        doc.save(ignore_permissions=True)
    else:
        doc.insert(ignore_permissions=True)
    _set_project_permission(doc.name, project)
    frappe.clear_cache(user=doc.name)
    return {"user_id": doc.name, "created": not exists}


@frappe.whitelist(methods=["POST"])
def set_user_enabled(user: str, enabled: int | str) -> dict[str, Any]:
    _require_management()
    user = str(user or "").strip()
    target = cint(enabled)
    if not user or not frappe.db.exists("User", user):
        frappe.throw(_("El usuario no existe."))
    if user in {"Administrator", frappe.session.user} and not target:
        frappe.throw(_("No puede suspender esta cuenta mientras está en uso."))
    frappe.db.set_value("User", user, "enabled", target)
    frappe.clear_cache(user=user)
    return {"user_id": user, "enabled": target}


__all__ = ["get_user_center", "save_user", "set_user_enabled"]
