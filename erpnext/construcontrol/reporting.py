from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import flt, getdate, now_datetime, today

from erpnext.construcontrol.access import project_filter, require_construcontrol_access
from erpnext.construcontrol.business_rules import expense_amounts

_READER_ROLES = {
    "System Manager",
    "ConstruControl Manager",
    "ConstruControl Operator",
    "ConstruControl Auditor",
    "ConstruControl Viewer",
}
_WRITER_ROLES = {"System Manager", "ConstruControl Manager", "ConstruControl Operator"}
_ROLE_LABELS = (
    ("System Manager", "ADMIN"),
    ("ConstruControl Manager", "MANAGER"),
    ("ConstruControl Operator", "OPERATOR"),
    ("ConstruControl Auditor", "AUDITOR"),
    ("ConstruControl Viewer", "VIEWER"),
)


def _require(roles: set[str], message: str) -> None:
    if not (roles & set(frappe.get_roles())):
        frappe.throw(_(message), frappe.PermissionError)


def _role_label() -> str:
    roles = set(frappe.get_roles())
    for role, label in _ROLE_LABELS:
        if role in roles:
            return label
    return "USER"


def _full_name(user: str) -> str:
    return str(frappe.db.get_value("User", user, "full_name") or user)


def _period(date_from: str | None, date_to: str | None) -> tuple[Any, Any]:
    start = getdate(date_from) if date_from else getdate(today()).replace(day=1)
    end = getdate(date_to) if date_to else getdate(today())
    if start > end:
        frappe.throw(_("La fecha inicial no puede ser posterior a la fecha final."))
    return start, end


def _project_filter(project: str | None) -> dict[str, Any]:
    return project_filter(project)


def _sum(rows: list[Any], fieldname: str) -> float:
    return round(sum(flt(row.get(fieldname)) for row in rows), 2)


def _between(fieldname: str, start: Any, end: Any) -> list[Any]:
    return ["between", [start, end]]


@frappe.whitelist()
def get_reporting_summary(
    date_from: str | None = None,
    date_to: str | None = None,
    project: str | None = None,
) -> dict[str, Any]:
    _require(_READER_ROLES, "No tiene permiso para consultar reportes de ConstruControl.")
    require_construcontrol_access()
    start, end = _period(date_from, date_to)
    scoped = _project_filter(project)

    funds = frappe.get_all(
        "CC Funding Source",
        filters={**scoped, "is_logically_deleted": 0, "date_received": _between("date_received", start, end)},
        fields=["name", "status", "amount_hnl", "net_amount_hnl", "spent_hnl", "pending_hnl", "available_hnl"],
        order_by="date_received desc",
    )
    expenses = frappe.get_all(
        "CC Expense Control",
        filters={**scoped, "is_logically_deleted": 0, "posting_date": _between("posting_date", start, end)},
        fields=[
            "name", "status", "financial_status", "payment_status", "amount_hnl",
            "paid_amount_hnl", "balance_due_hnl", "professional_approval_status",
            "category", "provider_name",
        ],
        order_by="posting_date desc",
    )
    contracts = frappe.get_all(
        "CC Labor Contract",
        filters={**scoped, "is_logically_deleted": 0},
        fields=["name", "status", "project_value_hnl", "labor_value_hnl", "paid_hnl", "balance_hnl"],
    )
    phases = frappe.get_all(
        "CC Construction Phase",
        filters={**scoped, "is_logically_deleted": 0},
        fields=["name", "phase_name", "progress_percent", "budget_hnl", "status"],
        order_by="phase_order asc",
    )

    received_funds = [
        row for row in funds
        if str(row.get("status") or "received").lower() not in {"cancelled", "rejected"}
    ]
    received = round(sum(flt(row.get("net_amount_hnl") or row.get("amount_hnl")) for row in received_funds), 2)

    categories: dict[str, float] = {}
    providers: dict[str, float] = {}
    recognized = paid = pending = 0.0
    for row in expenses:
        row_recognized, row_paid, row_pending = expense_amounts(
            row.get("amount_hnl"),
            row.get("payment_status"),
            row.get("financial_status"),
            row.get("paid_amount_hnl"),
            row.get("balance_due_hnl"),
            row.get("professional_approval_status"),
        )
        recognized += row_recognized
        paid += row_paid
        pending += row_pending
        if row_recognized:
            category = str(row.get("category") or "other")
            provider = str(row.get("provider_name") or "Sin proveedor")
            categories[category] = round(categories.get(category, 0) + row_recognized, 2)
            providers[provider] = round(providers.get(provider, 0) + row_recognized, 2)

    recognized = round(recognized, 2)
    paid = round(paid, 2)
    pending = round(pending, 2)
    progress = round(sum(flt(row.progress_percent) for row in phases) / len(phases), 2) if phases else 0
    contracted = round(sum(flt(row.project_value_hnl or row.labor_value_hnl) for row in contracts), 2)
    contract_paid = _sum(contracts, "paid_hnl")

    return {
        "period": {"date_from": str(start), "date_to": str(end)},
        "project": project,
        "totals": {
            "received_hnl": received,
            "recognized_expense_hnl": recognized,
            "spent_hnl": paid,
            "pending_hnl": pending,
            "available_hnl": round(received - paid, 2),
            "projected_hnl": round(received - recognized, 2),
            "contracted_hnl": contracted,
            "contract_paid_hnl": contract_paid,
            "contract_balance_hnl": round(contracted - contract_paid, 2),
            "phase_budget_hnl": _sum(phases, "budget_hnl"),
            "overall_progress": progress,
        },
        "counts": {
            "funds": len(funds),
            "expenses": len(expenses),
            "contracts": len(contracts),
            "phases": len(phases),
        },
        "expense_categories": [
            {"label": label, "amount_hnl": amount}
            for label, amount in sorted(categories.items(), key=lambda item: item[1], reverse=True)
        ],
        "providers": [
            {"label": label, "amount_hnl": amount}
            for label, amount in sorted(providers.items(), key=lambda item: item[1], reverse=True)[:10]
        ],
        "phases": phases,
        "generated_at": str(now_datetime()),
        "generated_by": {
            "email": frappe.session.user,
            "name": _full_name(frappe.session.user),
            "role": _role_label(),
        },
    }


@frappe.whitelist(methods=["POST"])
def generate_report_record(
    report_type: str,
    date_from: str | None = None,
    date_to: str | None = None,
    project: str | None = None,
) -> dict[str, Any]:
    _require(_WRITER_ROLES, "No tiene permiso para generar registros de reporte.")
    require_construcontrol_access(write=True)
    allowed = {"financial", "expenses", "contracts", "phases", "weekly"}
    normalized_type = str(report_type or "financial").strip().casefold()
    if normalized_type not in allowed:
        frappe.throw(_("Tipo de reporte no permitido."))

    summary = get_reporting_summary(date_from=date_from, date_to=date_to, project=project)
    user = frappe.session.user
    identity = f"{now_datetime().isoformat()}|{user}|{normalized_type}|{summary['period']}|{project or ''}"
    source_key = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:40]
    title = f"BI01 · {normalized_type.upper()} · {summary['period']['date_from']} a {summary['period']['date_to']}"

    values = {
        "doctype": "CC Generated Report",
        "source_key": source_key,
        "source_id": source_key,
        "project": project,
        "code": f"BI01-{source_key[:10].upper()}",
        "title": title,
        "status": "generated",
        "posting_date": today(),
        "amount_hnl": summary["totals"]["spent_hnl"],
        "description": "Reporte generado desde datos vivos y conciliados de ConstruControl.",
        "report_type": normalized_type,
        "date_from": summary["period"]["date_from"],
        "date_to": summary["period"]["date_to"],
        "generated_at": now_datetime(),
        "generated_by_email": user,
        "generated_by_name": _full_name(user),
        "generated_by_role": _role_label(),
        "filters_json": json.dumps({"project": project}, ensure_ascii=False, sort_keys=True),
        "totals_json": json.dumps(summary["totals"], ensure_ascii=False, sort_keys=True),
        "payload_json": json.dumps(summary, ensure_ascii=False, sort_keys=True, default=str),
        "is_logically_deleted": 0,
    }
    allowed_fields = {field.fieldname for field in frappe.get_meta("CC Generated Report").fields}
    document = frappe.get_doc({key: value for key, value in values.items() if key == "doctype" or key in allowed_fields})
    document.insert()
    return {"name": document.name, "title": title, "summary": summary}


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
    if not frappe.db.exists("CC Notification Contact", contact):
        frappe.throw(_("El contacto no existe."))
    document = frappe.get_doc("CC Notification Contact", contact)
    if not document.has_permission("read"):
        frappe.throw(_("No tiene permiso para utilizar este contacto."), frappe.PermissionError)

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

    identity = f"{now_datetime().isoformat()}|{contact}|{event_type}|{body}"
    source_key = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:40]
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
            {"summary": summary, "related_doctype": related_doctype, "related_name": related_name},
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        ),
        "is_logically_deleted": 0,
    }
    allowed_fields = {field.fieldname for field in frappe.get_meta("CC Notification Log").fields}
    log = frappe.get_doc({key: value for key, value in values.items() if key == "doctype" or key in allowed_fields})
    log.insert()
    return {"log": log.name, "whatsapp_url": whatsapp_url, "message": body, "status": "prepared"}


@frappe.whitelist(methods=["POST"])
def mark_notification_sent(log_name: str) -> dict[str, Any]:
    _require(_WRITER_ROLES, "No tiene permiso para confirmar notificaciones.")
    require_construcontrol_access(write=True)
    log = frappe.get_doc("CC Notification Log", log_name)
    if not log.has_permission("write"):
        frappe.throw(_("No tiene permiso para modificar este registro."), frappe.PermissionError)
    if log.meta.has_field("project") and log.get("project"):
        project_filter(str(log.get("project")))
    if log.meta.has_field("delivery_status"):
        log.delivery_status = "sent_manual"
    if log.meta.has_field("sent_at"):
        log.sent_at = now_datetime()
    log.status = "sent_manual"
    log.save()
    return {"name": log.name, "status": "sent_manual"}
