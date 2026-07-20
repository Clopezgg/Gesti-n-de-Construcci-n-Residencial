from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, validate_email_address

from erpnext.construcontrol.audit import record_manual_event

MANAGEMENT = {"System Manager", "ConstruControl Manager"}
BUSINESS_ROLES = (
	"ConstruControl Manager",
	"ConstruControl Operator",
	"ConstruControl Auditor",
	"ConstruControl Viewer",
)
LIMITED_ROLES = set(BUSINESS_ROLES[1:])
ROLE_LABELS = {
	"System Manager": "ADMIN",
	"ConstruControl Manager": "MANAGER",
	"ConstruControl Operator": "OPERATOR",
	"ConstruControl Auditor": "AUDITOR",
	"ConstruControl Viewer": "VIEWER",
}


def _throw(message: str) -> None:
	frappe.throw(_(message), frappe.PermissionError)


def _require_management() -> None:
	if not (MANAGEMENT & set(frappe.get_roles())):
		_throw("No tiene permisos para administrar usuarios.")


def _require_system_manager() -> None:
	if "System Manager" not in set(frappe.get_roles()):
		_throw("Solo un administrador del sistema puede ejecutar esta operación.")


def _can_assign_system_manager() -> bool:
	return "System Manager" in set(frappe.get_roles())


def _target_has_system_manager(user: str) -> bool:
	return bool(
		frappe.db.exists(
			"Has Role",
			{"parent": str(user or "").strip(), "parenttype": "User", "role": "System Manager"},
		)
	)


def _is_admin_account(user: str) -> bool:
	user = str(user or "").strip()
	return user == "Administrator" or _target_has_system_manager(user)


def _enabled_system_managers(*, exclude: str = "") -> list[str]:
	users = {
		str(user)
		for user in frappe.get_all(
			"Has Role",
			filters={"parenttype": "User", "role": "System Manager"},
			pluck="parent",
		)
		if user
	}
	if frappe.db.exists("User", "Administrator"):
		users.add("Administrator")
	return sorted(
		user
		for user in users
		if user != str(exclude or "").strip() and cint(frappe.db.get_value("User", user, "enabled")) == 1
	)


def _require_target_management(user: str) -> None:
	if _is_admin_account(user) and not _can_assign_system_manager():
		_throw("Solo un administrador del sistema puede modificar una cuenta ADMIN.")


def _assert_admin_transition(
	user: str,
	*,
	new_role: str,
	enabled: int | str,
	deleting: bool = False,
) -> None:
	user = str(user or "").strip()
	if not _is_admin_account(user):
		return
	if not (deleting or new_role != "System Manager" or not cint(enabled)):
		return
	if user == "Administrator":
		_throw("La cuenta Administrator no puede suspenderse, degradarse ni eliminarse.")
	if user == frappe.session.user:
		_throw("No puede retirar privilegios administrativos de la cuenta que está utilizando.")
	_require_system_manager()
	if not _enabled_system_managers(exclude=user):
		_throw("La última cuenta ADMIN protegida no puede suspenderse, degradarse ni eliminarse.")


def _visible_role(roles: set[str]) -> str:
	for role in ("System Manager", *BUSINESS_ROLES):
		if role in roles:
			return ROLE_LABELS[role]
	return "USER"


def _role_from_label(label: str) -> str:
	reverse = {label: role for role, label in ROLE_LABELS.items()}
	role = reverse.get(str(label or "").strip().upper())
	if not role:
		frappe.throw(_("Seleccione un rol permitido: ADMIN, MANAGER, OPERATOR, AUDITOR o VIEWER."))
	if role == "System Manager" and not _can_assign_system_manager():
		_throw("Solo un administrador del sistema puede asignar el rol ADMIN.")
	return role


def _validate_project_assignment(role: str, project: str) -> str:
	project = str(project or "").strip()
	if role in LIMITED_ROLES and not project:
		frappe.throw(_("Asigne un proyecto a los usuarios OPERATOR, AUDITOR y VIEWER."))
	if project and not frappe.db.exists("Project", project):
		frappe.throw(_("El proyecto seleccionado no existe."))
	return project if role in LIMITED_ROLES else ""


def _user_roles(users: list[str]) -> dict[str, set[str]]:
	result: dict[str, set[str]] = defaultdict(set)
	for row in frappe.get_all(
		"Has Role",
		filters={"parent": ["in", users], "role": ["in", ["System Manager", *BUSINESS_ROLES]]},
		fields=["parent", "role"],
	):
		result[str(row.get("parent"))].add(str(row.get("role")))
	return result


def _project_permissions(users: list[str]) -> dict[str, list[str]]:
	result: dict[str, list[str]] = defaultdict(list)
	for row in frappe.get_all(
		"User Permission",
		filters={"user": ["in", users], "allow": "Project"},
		fields=["user", "for_value", "is_default"],
		order_by="is_default desc, creation asc",
	):
		if row.get("for_value"):
			result[str(row.get("user"))].append(str(row.get("for_value")))
	return result


def _snapshot(user: str) -> dict[str, Any]:
	if not user or not frappe.db.exists("User", user):
		return {"user_id": user, "exists": False}
	roles = set(frappe.get_roles(user))
	return {
		"user_id": user,
		"exists": True,
		"enabled": cint(frappe.db.get_value("User", user, "enabled")),
		"role": _visible_role(roles),
		"roles": sorted(roles & {"System Manager", *BUSINESS_ROLES}),
		"projects": _project_permissions([user]).get(user, []),
	}


def _audit(action: str, user: str, before: dict[str, Any], after: dict[str, Any], reason: str = "") -> None:
	if not frappe.db.exists("DocType", "CC Audit Log"):
		return
	record_manual_event(
		module="US01",
		action=action,
		record_type="User",
		record_id=user,
		previous_state=before,
		next_state=after,
		reason=reason or None,
	)


def _legacy_access(users: list[str]) -> dict[str, dict[str, Any]]:
	if not users or not frappe.db.exists("DocType", "CC User Access"):
		return {}
	result: dict[str, dict[str, Any]] = {}
	for row in frappe.get_all(
		"CC User Access",
		filters={"email": ["in", users], "is_logically_deleted": 0},
		fields=["email", "source_id", "provider", "access_status"],
		order_by="modified desc",
	):
		result.setdefault(str(row.get("email")), dict(row))
	return result


@frappe.whitelist()
def get_user_center(search: str = "", enabled: str | int | None = None) -> dict[str, Any]:
	_require_management()
	filters: dict[str, Any] = {"user_type": "System User", "name": ["not in", ["Guest"]]}
	if enabled not in (None, ""):
		filters["enabled"] = cint(enabled)
	or_filters = None
	if search := str(search or "").strip():
		like = f"%{search}%"
		or_filters = {field: ["like", like] for field in ("name", "full_name", "email")}
	rows = frappe.get_all(
		"User",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name",
			"email",
			"full_name",
			"first_name",
			"last_name",
			"enabled",
			"last_login",
			"last_active",
			"user_image",
		],
		order_by="enabled desc, full_name asc, name asc",
		limit_page_length=500,
	)
	names = [str(row.get("name")) for row in rows]
	roles = _user_roles(names)
	projects = _project_permissions(names)
	legacy = _legacy_access(names)
	users = []
	for row in rows:
		user = str(row.get("name"))
		historical = legacy.get(user, {})
		users.append(
			{
				"user_id": user,
				"email": row.get("email") or user,
				"display_name": row.get("full_name") or user,
				"first_name": row.get("first_name") or "",
				"last_name": row.get("last_name") or "",
				"enabled": cint(row.get("enabled")),
				"role": _visible_role(roles.get(user, set())),
				"roles": sorted(roles.get(user, set())),
				"projects": projects.get(user, []),
				"last_login": row.get("last_login"),
				"last_active": row.get("last_active"),
				"user_image": row.get("user_image") or "",
				"protected": _is_admin_account(user) or user == frappe.session.user,
				"historical_source_id": historical.get("source_id"),
				"historical_provider": historical.get("provider"),
				"historical_status": historical.get("access_status"),
			}
		)
	return {
		"users": users,
		"projects": frappe.get_all(
			"Project",
			filters={"is_active": "Yes"},
			fields=["name", "project_name"],
			order_by="project_name asc",
		),
		"roles": list(ROLE_LABELS.values()),
		"can_assign_admin": _can_assign_system_manager(),
		"can_delete_users": _can_assign_system_manager(),
	}


def _set_business_role(doc: Any, role: str) -> None:
	keep = [row.role for row in doc.roles if row.role not in {"System Manager", *BUSINESS_ROLES}]
	doc.set("roles", [])
	for existing in keep:
		doc.append("roles", {"role": existing})
	doc.append("roles", {"role": role})


def _set_project_permission(user: str, project: str) -> None:
	for name in frappe.get_all("User Permission", filters={"user": user, "allow": "Project"}, pluck="name"):
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
	if not email or not validate_email_address(email, throw=False):
		frappe.throw(_("Ingrese un correo electrónico válido."))
	if not first_name:
		frappe.throw(_("El nombre es obligatorio."))
	if len(first_name) > 140 or len(last_name) > 140:
		frappe.throw(_("El nombre supera la longitud permitida."))
	internal_role = _role_from_label(role)
	project = _validate_project_assignment(internal_role, project)
	target_enabled = cint(enabled)
	exists = bool(frappe.db.exists("User", email))
	before = _snapshot(email)
	if exists:
		_require_target_management(email)
		_assert_admin_transition(email, new_role=internal_role, enabled=target_enabled)
		doc = frappe.get_doc("User", email)
	else:
		doc = frappe.new_doc("User")
		doc.email = email
		doc.user_type = "System User"
		doc.send_welcome_email = 0
	doc.first_name, doc.last_name, doc.enabled = first_name, last_name, target_enabled
	_set_business_role(doc, internal_role)
	(doc.save if exists else doc.insert)(ignore_permissions=True)
	_set_project_permission(doc.name, project)
	frappe.clear_cache(user=doc.name)
	_audit("UPDATE" if exists else "CREATE", doc.name, before, _snapshot(doc.name))
	return {"user_id": doc.name, "created": not exists}


@frappe.whitelist(methods=["POST"])
def approve_user(user: str) -> dict[str, Any]:
	_require_management()
	user = str(user or "").strip()
	if not user or not frappe.db.exists("User", user):
		frappe.throw(_("El usuario no existe."))
	_require_target_management(user)
	before = _snapshot(user)
	role = next(
		(role for role in ("System Manager", *BUSINESS_ROLES) if role in set(frappe.get_roles(user))), ""
	)
	if not role:
		frappe.throw(_("El usuario no tiene un rol ConstruControl permitido."))
	projects = _project_permissions([user]).get(user, [])
	_validate_project_assignment(role, projects[0] if projects else "")
	frappe.db.set_value("User", user, "enabled", 1)
	frappe.clear_cache(user=user)
	_audit("APPROVE", user, before, _snapshot(user))
	return {"user_id": user, "enabled": 1, "approved": True}


@frappe.whitelist(methods=["POST"])
def set_user_enabled(user: str, enabled: int | str) -> dict[str, Any]:
	_require_management()
	user, target = str(user or "").strip(), cint(enabled)
	if not user or not frappe.db.exists("User", user):
		frappe.throw(_("El usuario no existe."))
	_require_target_management(user)
	role = next(
		(role for role in ("System Manager", *BUSINESS_ROLES) if role in set(frappe.get_roles(user))), ""
	)
	_assert_admin_transition(user, new_role=role, enabled=target)
	if user == frappe.session.user and not target:
		_throw("No puede suspender esta cuenta mientras está en uso.")
	before = _snapshot(user)
	frappe.db.set_value("User", user, "enabled", target)
	frappe.clear_cache(user=user)
	_audit("REACTIVATE" if target else "SUSPEND", user, before, _snapshot(user))
	return {"user_id": user, "enabled": target}


@frappe.whitelist(methods=["POST"])
def delete_user(user: str, reason: str = "") -> dict[str, Any]:
	_require_system_manager()
	user = str(user or "").strip()
	if not user or not frappe.db.exists("User", user):
		frappe.throw(_("El usuario no existe."))
	if user == frappe.session.user:
		_throw("No puede eliminar la cuenta que está utilizando.")
	_assert_admin_transition(user, new_role="", enabled=0, deleting=True)
	before = _snapshot(user)
	for name in frappe.get_all("User Permission", filters={"user": user}, pluck="name"):
		frappe.delete_doc("User Permission", name, ignore_permissions=True, force=True)
	frappe.delete_doc("User", user, ignore_permissions=True)
	frappe.clear_cache(user=user)
	_audit("DELETE", user, before, {"user_id": user, "exists": False}, reason)
	return {"user_id": user, "deleted": True}


__all__ = ["approve_user", "delete_user", "get_user_center", "save_user", "set_user_enabled"]
