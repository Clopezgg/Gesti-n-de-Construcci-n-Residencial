from __future__ import annotations

import re
from calendar import monthrange
from collections.abc import Mapping
from datetime import date
from typing import Any

import frappe
from frappe import _

from nexora.email_prompt_policy import (
	pending_emails_are_generic,
	remove_prompt_user,
	split_prompt_users,
)
from nexora.permissions import has_action, require_action, require_project_access

ACTIVE_PROJECT_KEY = "nexora_active_project"
ACTIVE_PERIOD_KEY = "nexora_active_period"
PERIOD_PATTERN = re.compile(r"^(?P<year>\d{4})-(?P<month>0[1-9]|1[0-2])$")
ROLE_LABELS = {
	"System Manager": _("Administrador del sistema"),
	"NEXORA Administrator": _("Administrador de NEXORA"),
	"NEXORA Finance Manager": _("Gerente financiero"),
	"NEXORA Finance Operator": _("Operador financiero"),
	"NEXORA Auditor": _("Auditor"),
	"NEXORA Project Viewer": _("Consulta de proyecto"),
}
ROLE_PRIORITY = tuple(ROLE_LABELS)


def suppress_generic_email_password_prompt(bootinfo: Any) -> None:
	"""Hide Frappe's email-password setup dialog only for known placeholder accounts.

	This changes the boot response, not the stored User or Email Account records. Real pending
	email accounts continue to trigger Frappe's normal password validation dialog.
	"""
	sysdefaults = getattr(bootinfo, "sysdefaults", None)
	if sysdefaults is None and isinstance(bootinfo, dict):
		sysdefaults = bootinfo.get("sysdefaults")
	if not isinstance(sysdefaults, dict):
		return

	prompt_value = sysdefaults.get("email_user_password")
	user = str(getattr(frappe.session, "user", "") or "")
	if not user or user not in split_prompt_users(prompt_value):
		return

	pending_email_ids = frappe.get_all(
		"User Email",
		filters={
			"parent": user,
			"parenttype": "User",
			"parentfield": "user_emails",
			"awaiting_password": 1,
		},
		pluck="email_id",
	)
	if not pending_emails_are_generic(pending_email_ids):
		return

	updated_value = remove_prompt_user(prompt_value, user)
	if updated_value is None:
		sysdefaults.pop("email_user_password", None)
	else:
		sysdefaults["email_user_password"] = updated_value


def _payload(value: str | Mapping[str, Any] | None) -> dict[str, Any]:
	if value is None:
		return {}
	data = dict(value) if isinstance(value, Mapping) else frappe.parse_json(value)
	if not isinstance(data, dict):
		frappe.throw(_("El contexto de NEXORA debe ser un objeto JSON."))
	return data


def _normalize_period(value: object, *, fallback: bool = False) -> str:
	text = str(value or "").strip()
	if not text and fallback:
		text = str(frappe.utils.today())[:7]
	match = PERIOD_PATTERN.fullmatch(text)
	if not match:
		frappe.throw(_("El período activo debe usar el formato AAAA-MM."))
	year = int(match.group("year"))
	month = int(match.group("month"))
	if year < 1900 or year > 9999:
		frappe.throw(_("El año del período activo está fuera del rango permitido."))
	return f"{year:04d}-{month:02d}"


def _period_bounds(period: str) -> tuple[str, str]:
	year, month = (int(part) for part in period.split("-", 1))
	last_day = monthrange(year, month)[1]
	return date(year, month, 1).isoformat(), date(year, month, last_day).isoformat()


def _safe_saved_project(project: str | None, user: str) -> str | None:
	if not project:
		return None
	try:
		require_project_access(project, action="view_reports", user=user)
	except (frappe.PermissionError, frappe.ValidationError):
		return None
	return project


def _visible_roles(user: str) -> list[str]:
	roles = set(frappe.get_roles(user))
	return [role for role in ROLE_PRIORITY if role in roles]


def _context_payload(user: str | None = None) -> dict[str, Any]:
	actor = user or frappe.session.user
	project = _safe_saved_project(
		str(frappe.defaults.get_user_default(ACTIVE_PROJECT_KEY) or "").strip() or None,
		actor,
	)
	saved_period = str(frappe.defaults.get_user_default(ACTIVE_PERIOD_KEY) or "").strip()
	try:
		period = _normalize_period(saved_period, fallback=True)
	except frappe.ValidationError:
		period = str(frappe.utils.today())[:7]
	from_date, to_date = _period_bounds(period)
	roles = _visible_roles(actor)
	project_label = (
		str(frappe.db.get_value("Project", project, "project_name") or project) if project else _("Todos los proyectos")
	)
	full_name = str(frappe.db.get_value("User", actor, "full_name") or actor)
	primary_role = roles[0] if roles else ""
	return {
		"project": project,
		"project_label": project_label,
		"period": period,
		"from_date": from_date,
		"to_date": to_date,
		"user": actor,
		"user_label": full_name,
		"roles": roles,
		"role_label": ROLE_LABELS.get(primary_role, _("Usuario NEXORA")),
		"can_view_all_projects": has_action("view_all_projects", actor),
		"can_view_financial_details": has_action("view_financial_details", actor),
		"requires_project_selection": not project and not has_action("view_all_projects", actor),
	}


@frappe.whitelist(methods=["GET"])
def get_active_context() -> dict[str, Any]:
	"""Return the persisted user context after server-side permission validation."""
	require_action("preview")
	return _context_payload()


@frappe.whitelist(methods=["POST"])
def set_active_context(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Persist project and period only after validating the current user's access."""
	require_action("preview")
	data = _payload(payload)
	project = str(data.get("project") or "").strip() or None
	period = _normalize_period(data.get("period"), fallback=True)
	if project:
		require_project_access(project, action="view_reports")
	elif not has_action("view_all_projects"):
		frappe.throw(
			_("Seleccione un proyecto autorizado antes de continuar."),
			frappe.PermissionError,
		)
	frappe.defaults.set_user_default(ACTIVE_PROJECT_KEY, project or "")
	frappe.defaults.set_user_default(ACTIVE_PERIOD_KEY, period)
	return _context_payload()
