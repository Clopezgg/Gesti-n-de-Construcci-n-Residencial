from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

_ALLOWED_CATEGORIES = {"core", "data", "communication", "finance", "document", "custom"}
_ALLOWED_PROVIDERS = {"erpnext_core", "supabase", "email", "whatsapp", "webhook", "api", "custom"}


def _require_system_manager() -> None:
	if "System Manager" not in set(frappe.get_roles()):
		frappe.throw(_("Solo un administrador puede modificar integraciones."), frappe.PermissionError)


def _safe_row(doc: Any) -> dict[str, Any]:
	return {
		"name": doc.name,
		"integration_code": doc.integration_code,
		"integration_name": doc.integration_name,
		"category": doc.category,
		"provider_type": doc.provider_type,
		"description": doc.description,
		"icon_file": doc.icon_file,
		"brand_color": doc.brand_color,
		"endpoint_url": doc.endpoint_url,
		"auth_mode": doc.auth_mode,
		"credential_configured": bool(doc.get_password("credential_secret", raise_exception=False)),
		"enabled": cint(doc.enabled),
		"status": doc.status,
		"last_test_at": doc.last_test_at,
		"last_test_status": doc.last_test_status,
		"last_test_message": doc.last_test_message,
		"last_used_at": doc.last_used_at,
		"is_protected": cint(doc.is_protected),
		"is_logically_deleted": cint(doc.is_logically_deleted),
	}


def _validate_endpoint(endpoint: str) -> None:
	if not endpoint:
		return
	parsed = urlparse(endpoint)
	if parsed.scheme != "https" or not parsed.hostname:
		frappe.throw(_("Las integraciones externas deben utilizar una URL HTTPS válida."))
	hostname = parsed.hostname.casefold()
	blocked = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
	if hostname in blocked or hostname.endswith(".local"):
		frappe.throw(_("No se permiten destinos locales o privados en integraciones personalizadas."))


@frappe.whitelist()
def list_integrations(include_archived: int = 0) -> list[dict[str, Any]]:
	filters: dict[str, Any] = {}
	if not cint(include_archived):
		filters["is_logically_deleted"] = 0
	names = frappe.get_all(
		"CC Integration Registry",
		filters=filters,
		pluck="name",
		order_by="sort_order asc, integration_name asc",
	)
	return [_safe_row(frappe.get_doc("CC Integration Registry", name)) for name in names]


@frappe.whitelist(methods=["POST"])
def create_custom_integration(
	integration_name: str,
	category: str = "custom",
	provider_type: str = "custom",
	endpoint_url: str = "",
	description: str = "",
) -> dict[str, Any]:
	_require_system_manager()
	name = str(integration_name or "").strip()
	category = str(category or "custom").strip().lower()
	provider_type = str(provider_type or "custom").strip().lower()
	endpoint_url = str(endpoint_url or "").strip()
	if not name:
		frappe.throw(_("El nombre de la integración es obligatorio."))
	if category not in _ALLOWED_CATEGORIES or provider_type not in _ALLOWED_PROVIDERS:
		frappe.throw(_("Categoría o proveedor de integración no permitido."))
	_validate_endpoint(endpoint_url)

	base = frappe.scrub(name).upper()[:44] or "CUSTOM"
	code = base
	suffix = 1
	while frappe.db.exists("CC Integration Registry", code):
		suffix += 1
		code = f"{base[:39]}_{suffix}"

	doc = frappe.get_doc(
		{
			"doctype": "CC Integration Registry",
			"integration_code": code,
			"source_key": f"integration:custom:{code.casefold()}",
			"source_id": code,
			"integration_name": name,
			"category": category,
			"provider_type": provider_type,
			"description": str(description or "").strip(),
			"endpoint_url": endpoint_url,
			"auth_mode": "none" if not endpoint_url else "api_key",
			"enabled": 0,
			"status": "draft",
			"last_test_status": "not_tested",
			"is_protected": 0,
			"is_logically_deleted": 0,
			"payload_json": json.dumps({"created_by": frappe.session.user}, sort_keys=True),
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return _safe_row(doc)


@frappe.whitelist(methods=["POST"])
def set_integration_enabled(name: str, enabled: int) -> dict[str, Any]:
	_require_system_manager()
	doc = frappe.get_doc("CC Integration Registry", name)
	if doc.is_logically_deleted:
		frappe.throw(_("Reactive la integración archivada antes de habilitarla."))
	doc.enabled = cint(enabled)
	doc.status = "configured" if doc.enabled else "disabled"
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return _safe_row(doc)


@frappe.whitelist(methods=["POST"])
def test_integration(name: str) -> dict[str, Any]:
	_require_system_manager()
	doc = frappe.get_doc("CC Integration Registry", name)
	provider = str(doc.provider_type or "custom")
	passed = False
	warning = False
	message = ""

	if provider == "erpnext_core":
		passed = bool(
			frappe.db.exists("DocType", "Project") and frappe.db.exists("DocType", "CC Project Profile")
		)
		message = (
			"Motor ERPNext y extensión ConstruControl disponibles."
			if passed
			else "Faltan componentes centrales del sistema."
		)
	elif provider == "email":
		passed = bool(frappe.db.exists("Email Account", {"enable_outgoing": 1}))
		message = (
			"Existe una cuenta de correo saliente activa."
			if passed
			else "No hay una cuenta de correo saliente activa."
		)
	elif provider == "supabase":
		passed = bool(
			frappe.db.exists(
				"ConstruControl Migration Run",
				{"dry_run": 0, "status": ["in", ["Completed", "Completed with Warnings"]]},
			)
		)
		message = (
			"La migración histórica de Supabase está registrada y conciliada."
			if passed
			else "No se encontró una migración histórica conciliada."
		)
	else:
		endpoint = str(doc.endpoint_url or "").strip()
		_validate_endpoint(endpoint)
		configured_secret = bool(doc.get_password("credential_secret", raise_exception=False))
		if endpoint and (doc.auth_mode in {"none", "managed"} or configured_secret):
			warning = True
			message = "Configuración local válida. La conexión externa no se ejecuta automáticamente por seguridad; use un adaptador autorizado."
		else:
			message = "Complete la URL HTTPS y la credencial requerida."

	doc.last_test_at = now_datetime()
	doc.last_test_status = "passed" if passed else "warning" if warning else "failed"
	doc.last_test_message = message
	doc.status = "healthy" if passed else "warning" if warning else "error"
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return _safe_row(doc)


@frappe.whitelist(methods=["POST"])
def archive_integration(name: str, archived: int = 1) -> dict[str, Any]:
	_require_system_manager()
	doc = frappe.get_doc("CC Integration Registry", name)
	if doc.is_protected and cint(archived):
		frappe.throw(_("Las integraciones esenciales pueden desactivarse, pero no archivarse."))
	doc.is_logically_deleted = cint(archived)
	doc.enabled = 0 if doc.is_logically_deleted else doc.enabled
	doc.status = "archived" if doc.is_logically_deleted else "disabled"
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return _safe_row(doc)


@frappe.whitelist(methods=["POST"])
def delete_custom_integration(name: str, confirmation: str) -> dict[str, Any]:
	_require_system_manager()
	if str(confirmation or "").strip().upper() != "ELIMINAR":
		frappe.throw(_("Escriba ELIMINAR para confirmar."))
	doc = frappe.get_doc("CC Integration Registry", name)
	if doc.is_protected:
		frappe.throw(_("Una integración esencial no puede eliminarse."), frappe.PermissionError)
	integration_name = doc.integration_name
	frappe.delete_doc("CC Integration Registry", doc.name, ignore_permissions=True)
	frappe.db.commit()
	return {"deleted": True, "integration_name": integration_name}


__all__ = [
	"archive_integration",
	"create_custom_integration",
	"delete_custom_integration",
	"list_integrations",
	"set_integration_enabled",
	"test_integration",
]
