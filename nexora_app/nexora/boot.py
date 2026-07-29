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
SEARCH_EXTENSION_TARGETS = (
	{
		"doctype": "Project",
		"label": "Proyecto",
		"title_field": "project_name",
		"project_field": "name",
		"fields": ("name", "project_name", "status"),
		"search_fields": ("name", "project_name"),
	},
	{
		"doctype": "NXR Financial Account",
		"label": "Cuenta guardada",
		"title_field": "account_name",
		"project_field": "project",
		"fields": (
			"name",
			"account_name",
			"project",
			"origin_or_sender",
			"institution",
			"account_reference",
			"currency",
			"default_channel",
			"active",
		),
		"search_fields": (
			"name",
			"account_name",
			"origin_or_sender",
			"institution",
			"account_reference",
		),
	},
	{
		"doctype": "NXR Operation",
		"label": "Movimiento",
		"title_field": "document_number",
		"project_field": "project",
		"fields": (
			"name",
			"document_number",
			"status",
			"project",
			"operation_type",
			"operation_date",
			"amount_hnl",
			"currency",
			"beneficiary",
			"external_reference",
			"evidence",
			"reference_name",
			"reversal_of",
			"substitutes_operation",
		),
		"search_fields": (
			"name",
			"document_number",
			"beneficiary",
			"external_reference",
			"reference_name",
		),
	},
	{
		"doctype": "NXR Fund Source",
		"label": "Fondo",
		"title_field": "source_name",
		"project_field": "project",
		"fields": (
			"name",
			"source_code",
			"source_name",
			"status",
			"project",
			"source_date",
			"amount_hnl",
			"currency",
			"origin_or_sender",
			"institution",
			"account_reference",
			"external_reference",
			"evidence",
		),
		"search_fields": (
			"source_code",
			"source_name",
			"origin_or_sender",
			"institution",
			"account_reference",
			"external_reference",
		),
	},
)
PROJECT_SCOPED_DOCTYPES = {
	"NXR Contract",
	"NXR Purchase Request",
	"NXR Purchase Order",
	"NXR Goods Receipt",
	"NXR Budget",
	"NXR Operation",
	"NXR Commitment",
	"NXR Evidence",
	"NXR Fund Source",
	"NXR Financial Account",
	"NXR Stock Transaction",
}
SEARCH_DETAIL_DOCTYPES = {
	"Project",
	"NXR Entity",
	"NXR Contract",
	"NXR Contractor Profile",
	"NXR Supplier Profile",
	"NXR Purchase Request",
	"NXR Purchase Order",
	"NXR Goods Receipt",
	"NXR Budget",
	"NXR Operation",
	"NXR Commitment",
	"NXR Evidence",
	"NXR Fund Source",
	"NXR Financial Account",
	"NXR Stock Transaction",
}


def suppress_generic_email_password_prompt(bootinfo: Any) -> None:
	"""Hide Frappe's email-password setup dialog only for known placeholder accounts."""
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
		str(frappe.db.get_value("Project", project, "project_name") or project)
		if project
		else _("Todos los proyectos")
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


def _mask_account(value: object) -> str:
	text = str(value or "").strip()
	if not text:
		return ""
	return f"•••• {text[-4:]}" if len(text) > 4 else "••••"


def _authorized_project(project: object) -> bool:
	name = str(project or "").strip()
	if not name:
		return has_action("view_all_projects")
	try:
		require_project_access(name, action="view_reports")
	except (frappe.PermissionError, frappe.ValidationError):
		return False
	return True


def _extension_rows(query: str, limit: int) -> list[dict[str, Any]]:
	results: list[dict[str, Any]] = []
	for target in SEARCH_EXTENSION_TARGETS:
		if not frappe.has_permission(target["doctype"], ptype="read"):
			continue
		remaining = limit - len(results)
		if remaining <= 0:
			break
		or_filters = [[field, "like", f"%{query}%"] for field in target["search_fields"]]
		try:
			rows = frappe.get_all(
				target["doctype"],
				fields=list(target["fields"]),
				or_filters=or_filters,
				limit_page_length=remaining,
			)
		except (frappe.DoesNotExistError, frappe.ValidationError):
			continue
		for row in rows:
			project = row.get(target["project_field"])
			if not _authorized_project(project):
				continue
			account = row.get("account_reference")
			if account:
				row["account_reference"] = _mask_account(account)
			results.append(
				{
					"doctype": target["doctype"],
					"label": target["label"],
					"name": row["name"],
					"title": row.get(target["title_field"]) or row["name"],
					"status": row.get("status") or ("Activo" if row.get("active") else ""),
					"document_number": row.get("document_number") or row.get("source_code") or "",
					"project": project,
					"summary": {
						"date": row.get("operation_date") or row.get("source_date") or "",
						"counterparty": row.get("beneficiary") or row.get("origin_or_sender") or "",
						"amount_hnl": row.get("amount_hnl"),
						"currency": row.get("currency") or "",
						"reference": row.get("external_reference") or "",
						"institution": row.get("institution") or "",
						"account": row.get("account_reference") or "",
					},
				}
			)
	return results


@frappe.whitelist(methods=["GET"])
def get_active_context() -> dict[str, Any]:
	require_action("preview")
	return _context_payload()


@frappe.whitelist(methods=["POST"])
def set_active_context(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("preview")
	data = _payload(payload)
	project = str(data.get("project") or "").strip() or None
	period = _normalize_period(data.get("period"), fallback=True)
	if project:
		require_project_access(project, action="view_reports")
	elif not has_action("view_all_projects"):
		frappe.throw(_("Seleccione un proyecto autorizado antes de continuar."), frappe.PermissionError)
	frappe.defaults.set_user_default(ACTIVE_PROJECT_KEY, project or "")
	frappe.defaults.set_user_default(ACTIVE_PERIOD_KEY, period)
	return _context_payload()


@frappe.whitelist(methods=["POST"])
def universal_search_consolidated(payload: str | Mapping[str, Any]) -> list[dict[str, Any]]:
	"""Use the canonical search and add missing operational fields without bypassing project access."""
	require_action("preview")
	data = _payload(payload)
	query = str(data.get("query") or "").strip()
	if not query:
		return []
	limit = min(max(int(data.get("limit") or 50), 1), 100)
	from nexora.dashboard.service import universal_search

	base = list(universal_search({**data, "limit": limit}))
	extended = _extension_rows(query, limit)
	scope = str(data.get("doctypes") or "").strip()
	combined: list[dict[str, Any]] = []
	seen: set[tuple[str, str]] = set()
	for row in [*base, *extended]:
		doctype = str(row.get("doctype") or "")
		name = str(row.get("name") or "")
		if scope and scope not in {str(row.get("label") or ""), doctype}:
			continue
		if doctype in PROJECT_SCOPED_DOCTYPES:
			project = row.get("project") or frappe.db.get_value(doctype, name, "project")
			if not _authorized_project(project):
				continue
			row["project"] = project
		key = (doctype, name)
		if not all(key) or key in seen:
			continue
		seen.add(key)
		combined.append(row)
		if len(combined) >= limit:
			break
	return combined


@frappe.whitelist(methods=["POST"])
def get_search_result_detail(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Return a bounded, permission-checked consolidated view for one search result."""
	require_action("preview")
	data = _payload(payload)
	doctype = str(data.get("doctype") or "").strip()
	name = str(data.get("name") or "").strip()
	if doctype not in SEARCH_DETAIL_DOCTYPES or not name:
		frappe.throw(_("El resultado solicitado no es válido."))
	doc = frappe.get_doc(doctype, name)
	if not frappe.has_permission(doctype, ptype="read", doc=doc):
		frappe.throw(_("No tiene permiso para consultar este documento."), frappe.PermissionError)
	project = str(getattr(doc, "project", "") or (name if doctype == "Project" else "")).strip()
	if project:
		require_project_access(project, action="view_reports")
	fields = {
		"doctype": doctype,
		"name": name,
		"title": getattr(doc, "document_number", None)
		or getattr(doc, "source_name", None)
		or getattr(doc, "display_name", None)
		or getattr(doc, "account_name", None)
		or getattr(doc, "project_name", None)
		or name,
		"document_number": getattr(doc, "document_number", "") or getattr(doc, "source_code", ""),
		"status": getattr(doc, "status", ""),
		"project": project,
		"date": getattr(doc, "operation_date", "") or getattr(doc, "source_date", ""),
		"counterparty": getattr(doc, "beneficiary", "") or getattr(doc, "origin_or_sender", ""),
		"amount_hnl": getattr(doc, "amount_hnl", None),
		"currency": getattr(doc, "currency", ""),
		"reference": getattr(doc, "external_reference", ""),
		"institution": getattr(doc, "institution", ""),
		"account": _mask_account(getattr(doc, "account_reference", "")),
		"evidence": getattr(doc, "evidence", ""),
		"relationships": {
			"reference_name": getattr(doc, "reference_name", ""),
			"reversal_of": getattr(doc, "reversal_of", ""),
			"substitutes_operation": getattr(doc, "substitutes_operation", ""),
			"commitment": getattr(doc, "commitment", ""),
		},
		"effects": [],
	}
	if doctype == "NXR Operation":
		fields["effects"] = frappe.get_all(
			"NXR Operation Effect",
			filters={"operation": name},
			fields=["fund_source", "dimension", "effect_type", "amount_hnl"],
			order_by="creation asc",
		)
	return fields
