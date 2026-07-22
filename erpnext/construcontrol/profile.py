from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

_ALLOWED_LANGUAGES = {"es", "en"}


def _require_authenticated_user() -> str:
	user = str(frappe.session.user or "").strip()
	if not user or user == "Guest":
		frappe.throw(_("Debe iniciar sesión para consultar su perfil."), frappe.PermissionError)
	return user


def _field(doc: Any, fieldname: str, default: Any = None) -> Any:
	return doc.get(fieldname) if doc.meta.has_field(fieldname) else default


def _visible_business_role() -> str:
	roles = set(frappe.get_roles())
	priorities = (
		("System Manager", "ADMIN"),
		("ConstruControl Manager", "MANAGER"),
		("ConstruControl Operator", "OPERATOR"),
		("ConstruControl Auditor", "AUDITOR"),
		("ConstruControl Viewer", "VIEWER"),
	)
	for internal, visible in priorities:
		if internal in roles:
			return visible
	return "USER"


def _assigned_projects(user: str) -> list[dict[str, Any]]:
	project_names = frappe.get_all(
		"User Permission",
		filters={"user": user, "allow": "Project", "is_default": ["in", [0, 1]]},
		pluck="for_value",
	)
	projects: list[dict[str, Any]] = []
	for name in project_names:
		values = frappe.db.get_value(
			"Project",
			name,
			["name", "project_name", "status", "percent_complete"],
			as_dict=True,
		)
		if values:
			projects.append(dict(values))
	return projects


def _recent_activity(user: str) -> list[dict[str, Any]]:
	filters: list[list[Any]] = [["CC Audit Log", "is_logically_deleted", "=", 0]]
	if frappe.get_meta("CC Audit Log").has_field("actor_email"):
		filters.append(["CC Audit Log", "actor_email", "=", user])
	else:
		filters.append(["CC Audit Log", "owner", "=", user])
	return frappe.get_all(
		"CC Audit Log",
		filters=filters,
		fields=["name", "posting_date", "action", "record_type", "record_id", "reason"],
		order_by="creation desc",
		limit_page_length=10,
	)


def _correction_security(user: str) -> dict[str, Any] | None:
	if user != "Administrator":
		return None
	from erpnext.construcontrol.admin_corrections import get_security_status

	return get_security_status()


@frappe.whitelist()
def get_my_profile() -> dict[str, Any]:
	user = _require_authenticated_user()
	doc = frappe.get_doc("User", user)
	roles = sorted(role for role in frappe.get_roles(user) if role not in {"All", "Guest", "Desk User"})
	return {
		"user_id": user,
		"display_name": frappe.utils.get_fullname(user) or user,
		"first_name": doc.first_name or "",
		"last_name": doc.last_name or "",
		"email": user,
		"mobile_no": _field(doc, "mobile_no", "") or _field(doc, "phone", "") or "",
		"user_image": _field(doc, "user_image", "") or "",
		"language": _field(doc, "language", "es") or "es",
		"time_zone": _field(doc, "time_zone", "")
		or frappe.db.get_single_value("System Settings", "time_zone"),
		"role": _visible_business_role(),
		"roles": roles,
		"enabled": cint(doc.enabled),
		"last_login": _field(doc, "last_login", None),
		"last_active": _field(doc, "last_active", None),
		"projects": _assigned_projects(user),
		"recent_activity": _recent_activity(user),
		"correction_security": _correction_security(user),
		"security": {
			"two_factor_enabled": cint(_field(doc, "two_factor_auth", 0)),
			"simultaneous_sessions": _field(doc, "simultaneous_sessions", None),
			"login_after": _field(doc, "login_after", None),
			"login_before": _field(doc, "login_before", None),
		},
	}


@frappe.whitelist(methods=["POST"])
def update_my_profile(
	first_name: str,
	last_name: str = "",
	mobile_no: str = "",
	language: str = "es",
	time_zone: str = "",
) -> dict[str, Any]:
	user = _require_authenticated_user()
	first_name = str(first_name or "").strip()
	last_name = str(last_name or "").strip()
	mobile_no = str(mobile_no or "").strip()
	language = str(language or "es").strip().lower()
	time_zone = str(time_zone or "").strip()

	if not first_name:
		frappe.throw(_("El nombre es obligatorio."))
	if len(first_name) > 140 or len(last_name) > 140 or len(mobile_no) > 40:
		frappe.throw(_("Uno de los datos del perfil supera la longitud permitida."))
	if language not in _ALLOWED_LANGUAGES:
		frappe.throw(_("Idioma no permitido."))

	doc = frappe.get_doc("User", user)
	doc.first_name = first_name
	doc.last_name = last_name
	if doc.meta.has_field("mobile_no"):
		doc.mobile_no = mobile_no
	elif doc.meta.has_field("phone"):
		doc.phone = mobile_no
	if doc.meta.has_field("language"):
		doc.language = language
	if time_zone and doc.meta.has_field("time_zone"):
		doc.time_zone = time_zone
	doc.save(ignore_permissions=True)
	frappe.clear_cache(user=user)
	return get_my_profile()


__all__ = ["get_my_profile", "update_my_profile"]
