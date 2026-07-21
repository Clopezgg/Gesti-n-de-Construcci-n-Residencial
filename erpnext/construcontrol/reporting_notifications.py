from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import now_datetime, today

from erpnext.construcontrol.access import (
	assert_project_access,
	require_construcontrol_access,
)
from erpnext.construcontrol.reporting_summary import get_reporting_summary
from erpnext.construcontrol.reporting_utils import (
	_WRITER_ROLES,
	_require,
	_require_exact_project,
)


def _phone_digits(value: str) -> str:
	return re.sub(r"\D", "", str(value or ""))


def _default_message(event_type: str, contact_name: str, summary: dict[str, Any]) -> str:
	totals = summary["totals"]
	event_label = {
		"income": "un ingreso o remesa",
		"expense": "un gasto",
		"material": "un movimiento de material",
		"inventory": "un movimiento de inventario",
		"progress": "un avance de obra",
		"weekly": "un cierre semanal",
		"report": "un reporte",
		"manual": "una actualización",
	}.get(event_type, "una actualización")
	return (
		f"Hola {contact_name}, ConstruControl registró {event_label}. "
		f"Disponible: L {totals['available_hnl']:,.2f}. "
		f"Gastado en el período: L {totals['spent_hnl']:,.2f}."
	)


@frappe.whitelist(methods=["POST"])
def prepare_notification(
	contact: str,
	event_type: str = "manual",
	date_from: str | None = None,
	date_to: str | None = None,
	project: str | None = None,
	message: str | None = None,
	related_doctype: str | None = None,
	related_name: str | None = None,
) -> dict[str, Any]:
	_require(_WRITER_ROLES, "No tiene permiso para preparar notificaciones.")
	require_construcontrol_access(write=True)
	project = _require_exact_project(project, write=True)
	if not frappe.db.exists("CC Notification Contact", contact):
		frappe.throw(_("El contacto no existe."))
	document = frappe.get_doc("CC Notification Contact", contact)
	if not document.has_permission("read"):
		frappe.throw(_("No tiene permiso para utilizar este contacto."), frappe.PermissionError)
	if document.meta.has_field("project") and document.get("project") not in {
		None,
		"",
		project,
	}:
		frappe.throw(_("El contacto pertenece a otro proyecto."), frappe.PermissionError)
	active = int(document.get("active") if document.meta.has_field("active") else 1)
	authorized = int(document.get("authorized") if document.meta.has_field("authorized") else 0)
	if not active or not authorized:
		frappe.throw(_("El contacto debe estar activo y autorizado antes de preparar una notificación."))
	phone = _phone_digits(document.get("phone") or "")
	if len(phone) < 8 or len(phone) > 15:
		frappe.throw(_("El número de teléfono del contacto no es válido."))
	summary = get_reporting_summary(date_from=date_from, date_to=date_to, project=project)
	contact_name = str(document.get("contact_name") or document.get("title") or "contacto")
	body = str(message or "").strip() or _default_message(str(event_type), contact_name, summary)
	if len(body) > 1500:
		frappe.throw(_("El mensaje supera el límite de 1500 caracteres."))
	whatsapp_url = f"https://wa.me/{phone}?text={quote(body)}"
	identity = f"{project}|{contact}|{event_type}|{body}"
	source_key = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:40]
	existing = frappe.db.get_value(
		"CC Notification Log",
		{"source_key": source_key, "is_logically_deleted": 0},
		["name", "whatsapp_url"],
		as_dict=True,
	)
	if existing:
		return {
			"log": existing.name,
			"whatsapp_url": existing.whatsapp_url,
			"message": body,
			"status": "prepared",
			"reused": True,
		}
	values = {
		"doctype": "CC Notification Log",
		"source_key": source_key,
		"source_id": source_key,
		"project": project,
		"code": f"NT-{source_key[:10].upper()}",
		"title": f"Notificación preparada para {contact_name}",
		"status": "prepared",
		"posting_date": today(),
		"description": body,
		"event_type": event_type,
		"channel": "whatsapp",
		"contact": contact,
		"recipient": phone,
		"message": body,
		"prepared_at": now_datetime(),
		"delivery_status": "prepared",
		"related_doctype": related_doctype,
		"related_name": related_name,
		"whatsapp_url": whatsapp_url,
		"payload_json": json.dumps(
			{
				"summary": summary,
				"related_doctype": related_doctype,
				"related_name": related_name,
			},
			ensure_ascii=False,
			sort_keys=True,
			default=str,
		),
		"is_logically_deleted": 0,
	}
	allowed_fields = {field.fieldname for field in frappe.get_meta("CC Notification Log").fields}
	log = frappe.get_doc(
		{key: value for key, value in values.items() if key == "doctype" or key in allowed_fields}
	)
	log.insert()
	return {
		"log": log.name,
		"whatsapp_url": whatsapp_url,
		"message": body,
		"status": "prepared",
		"reused": False,
	}


@frappe.whitelist(methods=["POST"])
def mark_notification_sent(log_name: str) -> dict[str, Any]:
	_require(_WRITER_ROLES, "No tiene permiso para confirmar notificaciones.")
	require_construcontrol_access(write=True)
	log = frappe.get_doc("CC Notification Log", log_name)
	if not log.has_permission("write"):
		frappe.throw(_("No tiene permiso para modificar este registro."), frappe.PermissionError)
	if log.meta.has_field("project") and log.get("project"):
		assert_project_access(str(log.get("project")), write=True)
	if str(log.get("delivery_status") or "") == "sent_manual":
		return {"name": log.name, "status": "sent_manual", "reused": True}
	if log.meta.has_field("delivery_status"):
		log.delivery_status = "sent_manual"
	if log.meta.has_field("sent_at"):
		log.sent_at = now_datetime()
	log.status = "sent_manual"
	log.save()
	return {"name": log.name, "status": "sent_manual", "reused": False}


__all__ = ["mark_notification_sent", "prepare_notification"]
