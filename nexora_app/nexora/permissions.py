from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

ACCESS_ROLES = {
	"System Manager",
	"NEXORA Administrator",
	"NEXORA Finance Manager",
	"NEXORA Finance Operator",
	"NEXORA Auditor",
	"NEXORA Project Viewer",
}
OPERATOR_ROLES = {
	"System Manager",
	"NEXORA Administrator",
	"NEXORA Finance Manager",
	"NEXORA Finance Operator",
}
MANAGER_ROLES = {"System Manager", "NEXORA Administrator", "NEXORA Finance Manager"}
ADMINISTRATOR_ONLY_ROLES = {"System Manager", "NEXORA Administrator"}
FINANCIAL_DETAIL_ROLES = {
	"System Manager",
	"NEXORA Administrator",
	"NEXORA Finance Manager",
	"NEXORA Finance Operator",
	"NEXORA Auditor",
	"NEXORA Project Viewer",
}
REPORT_EXPORT_ROLES = {
	"System Manager",
	"NEXORA Administrator",
	"NEXORA Finance Manager",
	"NEXORA Auditor",
}
ALL_PROJECT_ROLES = {
	"System Manager",
	"NEXORA Administrator",
	"NEXORA Finance Manager",
	"NEXORA Finance Operator",
	"NEXORA Auditor",
}
SENSITIVE_DIRECTORY_ROLES = {
	"System Manager",
	"NEXORA Administrator",
	"NEXORA Finance Manager",
	"NEXORA Auditor",
}
ACTION_ROLES = {
	"preview": ACCESS_ROLES,
	"view_reports": ACCESS_ROLES,
	"export_reports": REPORT_EXPORT_ROLES,
	"view_all_projects": ALL_PROJECT_ROLES,
	"view_financial_details": FINANCIAL_DETAIL_ROLES,
	"view_closings": ACCESS_ROLES,
	"save_closing": MANAGER_ROLES,
	"reconcile_source": MANAGER_ROLES,
	"read_balances": ACCESS_ROLES,
	"read_entities": ACCESS_ROLES,
	"read_sensitive_entity": SENSITIVE_DIRECTORY_ROLES,
	"read_contracts": ACCESS_ROLES,
	"read_purchases": ACCESS_ROLES,
	"create_source": OPERATOR_ROLES,
	"cancel_source": MANAGER_ROLES,
	"execute": OPERATOR_ROLES,
	"upload_evidence": OPERATOR_ROLES,
	"create_entity": OPERATOR_ROLES,
	"create_contract": OPERATOR_ROLES,
	"create_supplier": OPERATOR_ROLES,
	"create_purchase_request": OPERATOR_ROLES,
	"submit_purchase_request": OPERATOR_ROLES,
	"create_purchase_order": MANAGER_ROLES,
	"submit_purchase_order": MANAGER_ROLES,
	"approve_purchase_order": MANAGER_ROLES,
	"manage_warehouse": MANAGER_ROLES,
	"create_stock_transaction": OPERATOR_ROLES,
	"submit_stock_transaction": MANAGER_ROLES,
	"update_entity": OPERATOR_ROLES,
	"approve": MANAGER_ROLES,
	"review_evidence": MANAGER_ROLES,
	"return": MANAGER_ROLES,
	"reclassify": MANAGER_ROLES,
	"manage_entity": MANAGER_ROLES,
	"manage_entity_role": MANAGER_ROLES,
	"manage_entity_compliance": MANAGER_ROLES,
	"consolidate_entity": MANAGER_ROLES,
	"manage_contract": MANAGER_ROLES,
	"execute_contract": MANAGER_ROLES,
	"manage_supplier": MANAGER_ROLES,
	"approve_purchase_request": MANAGER_ROLES,
	"ai_manage_provider": MANAGER_ROLES,
	"ai_view_provider": REPORT_EXPORT_ROLES,
	"ai_manage_credential": ADMINISTRATOR_ONLY_ROLES,
	"ai_test_connection": MANAGER_ROLES,
	# Bloque 21: mismo criterio que sus equivalentes de IA — conectar/probar un
	# canal externo (credenciales de Meta) es tan sensible como una credencial de
	# proveedor de IA; vincular una identidad externa a un usuario real de NEXORA
	# es más sensible aún (decide quién puede actuar como quién por WhatsApp), así
	# que ninguna de las dos queda en manos de un simple "Finance Manager".
	"manage_channel_credential": ADMINISTRATOR_ONLY_ROLES,
	"manage_channel_account": ADMINISTRATOR_ONLY_ROLES,
	"view_channel": REPORT_EXPORT_ROLES,
	# Mismo criterio que `manage_channel_credential`: una conexión SAP guarda
	# credenciales de un sistema externo, así que conectarla o probarla queda
	# solo para Administrador. Enviar un documento ya conectado es una acción
	# financiera equivalente a aprobar o gestionar un contrato — Gerente
	# financiero o Administrador, nunca un operador.
	"manage_sap_connection": ADMINISTRATOR_ONLY_ROLES,
	"submit_sap_document": MANAGER_ROLES,
	"view_sap_connection": REPORT_EXPORT_ROLES,
	# Administración funcional de NEXORA (enmienda del propietario, 2026-08-16,
	# Constitución Cap. 14): activar/desactivar cuentas y asignar/revocar
	# roles de NEXORA es tan sensible como una credencial externa — decide
	# quién puede actuar como quién dentro de todo el sistema — así que queda
	# reservado al Administrador NEXORA, nunca a un Gerente financiero.
	"manage_users": ADMINISTRATOR_ONLY_ROLES,
	"view_users": ADMINISTRATOR_ONLY_ROLES,
}


def can_access_nexora() -> bool:
	if frappe.session.user == "Guest":
		return False
	return bool(ACCESS_ROLES.intersection(frappe.get_roles(frappe.session.user)))


def has_action(action: str, user: str | None = None) -> bool:
	actor = user or frappe.session.user
	if actor == "Guest":
		return False
	allowed = ACTION_ROLES.get(action)
	return bool(allowed and allowed.intersection(frappe.get_roles(actor)))


def required_role_label(action: str) -> str:
	return {
		"cancel_source": _("Gerente financiero o Administrador"),
		"approve": _("Gerente financiero o Administrador"),
		"save_closing": _("Gerente financiero o Administrador"),
		"reconcile_source": _("Gerente financiero o Administrador"),
		"export_reports": _("Auditor, Gerente financiero o Administrador"),
		"execute": _("Operador financiero, Gerente financiero o Administrador"),
		"create_purchase_order": _("Gerente financiero o Administrador"),
		"submit_purchase_order": _("Gerente financiero o Administrador"),
		"approve_purchase_order": _("Gerente financiero o Administrador"),
		"manage_warehouse": _("Gerente financiero o Administrador"),
		"create_stock_transaction": _("Operador financiero, Gerente financiero o Administrador"),
		"submit_stock_transaction": _("Gerente financiero o Administrador"),
	}.get(action, _("un rol autorizado de NEXORA"))


def require_action(action: str, user: str | None = None) -> None:
	actor = user or frappe.session.user
	if actor == "Guest":
		frappe.throw(_("Debe iniciar sesión para continuar."), frappe.PermissionError)
	allowed = ACTION_ROLES.get(action)
	if not allowed:
		frappe.throw(
			_("Esta función no está configurada correctamente. Comuníquese con el administrador."),
			frappe.PermissionError,
		)
	if not allowed.intersection(frappe.get_roles(actor)):
		frappe.throw(
			_("No puede realizar esta acción. Se requiere: {0}.").format(required_role_label(action)),
			frappe.PermissionError,
		)


def _has_explicit_project_permission(project: str, user: str) -> bool:
	if user == "Administrator" or has_action("view_all_projects", user):
		return True
	if frappe.db.exists(
		"User Permission",
		{
			"user": user,
			"allow": "Project",
			"for_value": project,
		},
	):
		return True
	project_doc = frappe.get_doc("Project", project)
	return bool(frappe.has_permission("Project", ptype="read", doc=project_doc, user=user))


def require_project_access(
	project: str | None,
	*,
	action: str = "view_reports",
	user: str | None = None,
) -> None:
	actor = user or frappe.session.user
	require_action(action, actor)
	if not project:
		if not has_action("view_all_projects", actor):
			frappe.throw(
				_("Seleccione un proyecto autorizado para consultar esta información."),
				frappe.PermissionError,
			)
		return
	if not frappe.db.exists("Project", project):
		frappe.throw(_("El proyecto seleccionado no existe."))
	if not _has_explicit_project_permission(project, actor):
		frappe.throw(
			_("No tiene acceso al proyecto seleccionado."),
			frappe.PermissionError,
		)


def _search_payload(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = dict(payload) if isinstance(payload, Mapping) else frappe.parse_json(payload)
	if not isinstance(data, dict):
		frappe.throw(_("La búsqueda debe enviarse como un objeto JSON."))
	return data


def _row_is_readable(doctype: str, name: str, project: object = None) -> bool:
	if not frappe.has_permission(doctype, ptype="read"):
		return False
	try:
		doc = frappe.get_doc(doctype, name)
		if not frappe.has_permission(doctype, ptype="read", doc=doc):
			return False
		if project:
			require_project_access(str(project), action="view_reports")
		return True
	except (frappe.DoesNotExistError, frappe.PermissionError, frappe.ValidationError):
		return False


def _masked_account(value: object) -> str:
	text = str(value or "").strip()
	if not text:
		return ""
	return f"•••• {text[-4:]}" if len(text) > 4 else "••••"


def _safe_search_rows(
	*,
	doctype: str,
	label: str,
	title_field: str,
	search_fields: tuple[str, ...],
	query: str,
	limit: int,
	project_field: str = "project",
	extra_fields: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
	if not frappe.has_permission(doctype, ptype="read"):
		return []
	meta = frappe.get_meta(doctype)
	fields = ["name"]
	if title_field != "name" and meta.has_field(title_field):
		fields.append(title_field)
	for fieldname in ("status", "document_number", project_field, *extra_fields):
		if fieldname == "name" or not meta.has_field(fieldname) or fieldname in fields:
			continue
		fields.append(fieldname)
	rows = frappe.get_list(
		doctype,
		fields=fields,
		or_filters=[[fieldname, "like", f"%{query}%"] for fieldname in search_fields],
		limit_page_length=limit,
	)
	results: list[dict[str, Any]] = []
	for row in rows:
		name = str(row.get("name") or "")
		project = row.get(project_field) if project_field in row else None
		if not name or not _row_is_readable(doctype, name, project):
			continue
		results.append(
			{
				"doctype": doctype,
				"label": label,
				"name": name,
				"title": row.get(title_field) or row.get("document_number") or name,
				"status": row.get("status") or "",
				"document_number": row.get("document_number") or "",
				"project": project,
				"row": row,
			}
		)
	return results


@frappe.whitelist(methods=["POST"])
def secure_universal_search(payload: str | Mapping[str, Any]) -> list[dict[str, Any]]:
	"""Permission-aware replacement for the legacy universal search endpoint."""
	require_action("preview")
	data = _search_payload(payload)
	query = str(data.get("query") or "").strip()
	if not query:
		return []
	limit = min(max(int(data.get("limit") or 20), 1), 100)
	scope = data.get("doctypes")
	if isinstance(scope, str):
		scope = {"Movimiento": "Operación", "Fondo": "Fuente de fondos", "Comprobante": "Evidencia"}.get(
			scope, scope
		)
	from nexora.dashboard.service import SEARCHABLE_DOCTYPES

	entries = list(SEARCHABLE_DOCTYPES)
	if isinstance(scope, str) and scope:
		entries = [entry for entry in entries if entry["label"] == scope or entry["doctype"] == scope]
	elif isinstance(scope, list) and scope:
		entries = [entry for entry in entries if entry["doctype"] in scope]
	results: list[dict[str, Any]] = []
	for entry in entries:
		remaining = limit - len(results)
		if remaining <= 0:
			break
		results.extend(
			_safe_search_rows(
				doctype=entry["doctype"],
				label=entry["label"],
				title_field=entry["title_field"],
				search_fields=tuple(entry["search_fields"]),
				query=query,
				limit=remaining,
			)
		)
	return [{key: value for key, value in row.items() if key != "row"} for row in results[:limit]]


@frappe.whitelist(methods=["POST"])
def secure_universal_search_consolidated(payload: str | Mapping[str, Any]) -> list[dict[str, Any]]:
	"""Consolidated search with DocType, document and project permission checks on every row."""
	require_action("preview")
	data = _search_payload(payload)
	query = str(data.get("query") or "").strip()
	if not query:
		return []
	limit = min(max(int(data.get("limit") or 50), 1), 100)
	visible_scope = str(data.get("doctypes") or "").strip()
	canonical_scope = {
		"Movimiento": "Operación",
		"Fondo": "Fuente de fondos",
		"Comprobante": "Evidencia",
	}.get(visible_scope, visible_scope)
	base = secure_universal_search({**data, "doctypes": canonical_scope, "limit": limit})
	from nexora.boot import SEARCH_EXTENSION_TARGETS

	extended: list[dict[str, Any]] = []
	for target in SEARCH_EXTENSION_TARGETS:
		if visible_scope and visible_scope not in {target["label"], target["doctype"]}:
			continue
		remaining = limit - len(extended)
		if remaining <= 0:
			break
		rows = _safe_search_rows(
			doctype=target["doctype"],
			label=target["label"],
			title_field=target["title_field"],
			search_fields=tuple(target["search_fields"]),
			query=query,
			limit=remaining,
			project_field=target["project_field"],
			extra_fields=tuple(target["fields"]),
		)
		for item in rows:
			row = item.pop("row", {})
			account = _masked_account(row.get("account_reference"))
			item["document_number"] = item.get("document_number") or row.get("source_code") or ""
			item["summary"] = {
				"date": row.get("operation_date") or row.get("source_date") or "",
				"counterparty": row.get("beneficiary") or row.get("origin_or_sender") or "",
				"amount_hnl": row.get("amount_hnl"),
				"currency": row.get("currency") or "",
				"reference": row.get("external_reference") or "",
				"institution": row.get("institution") or "",
				"account": account,
			}
			extended.append(item)
	labels = {"Operación": "Movimiento", "Fuente de fondos": "Fondo", "Evidencia": "Comprobante"}
	combined: list[dict[str, Any]] = []
	seen: set[tuple[str, str]] = set()
	for item in [*base, *extended]:
		item["label"] = labels.get(str(item.get("label") or ""), str(item.get("label") or ""))
		if visible_scope and visible_scope not in {item["label"], item.get("doctype")}:
			continue
		key = (str(item.get("doctype") or ""), str(item.get("name") or ""))
		if not all(key) or key in seen:
			continue
		seen.add(key)
		combined.append(item)
		if len(combined) >= limit:
			break
	return combined
