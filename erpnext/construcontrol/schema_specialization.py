from __future__ import annotations

from typing import Any

import frappe

_GENERIC_LIST_FIELDS = ("source_id", "project", "code", "title", "status", "posting_date", "amount_hnl")

_SPECIALIZATIONS: dict[str, dict[str, Any]] = {
    "CC Funding Source": {
        "title_field": "title",
        "search_fields": "title,sender,reference,transaction_reference,financial_institution",
        "fields": {
            "title": {"label": "Concepto", "in_list_view": 1},
            "date_received": {"label": "Fecha recibida", "in_list_view": 1},
            "financial_institution": {"label": "Banco o remesadora", "in_list_view": 1},
            "net_amount_hnl": {"label": "Neto recibido (L)", "in_list_view": 1},
            "reconciliation_status": {"label": "Conciliación", "in_list_view": 1},
            "available_hnl": {"label": "Disponible (L)", "in_list_view": 1},
        },
    },
    "CC Expense Control": {
        "title_field": "title",
        "search_fields": "title,provider_name,invoice_number,folio,category",
        "fields": {
            "posting_date": {"label": "Fecha", "in_list_view": 1},
            "provider_name": {"label": "Proveedor", "in_list_view": 1},
            "category": {"label": "Categoría", "in_list_view": 1},
            "calculated_total_hnl": {"label": "Total (L)", "in_list_view": 1},
            "professional_approval_status": {"label": "Aprobación", "in_list_view": 1},
            "payment_status": {"label": "Pago", "in_list_view": 1},
        },
    },
    "CC Payable Control": {
        "title_field": "title",
        "search_fields": "provider_name,invoice_number,title,expense_control",
        "fields": {
            "provider_name": {"label": "Proveedor", "in_list_view": 1},
            "invoice_number": {"label": "Factura", "in_list_view": 1},
            "due_date": {"label": "Vencimiento", "in_list_view": 1},
            "balance_due_hnl": {"label": "Saldo pendiente (L)", "in_list_view": 1},
            "payable_status": {"label": "Estado", "in_list_view": 1},
        },
    },
    "CC Labor Contract": {
        "title_field": "contractor_name",
        "search_fields": "contractor_name,contract_code,title",
        "fields": {
            "contractor_name": {"label": "Contratista", "in_list_view": 1},
            "status": {"label": "Estado", "in_list_view": 1},
            "project_value_hnl": {"label": "Valor contratado (L)", "in_list_view": 1},
            "paid_hnl": {"label": "Pagado (L)", "in_list_view": 1},
            "balance_hnl": {"label": "Saldo (L)", "in_list_view": 1},
        },
    },
    "CC Construction Phase": {
        "title_field": "phase_name",
        "search_fields": "phase_name,title,status,schedule_status",
        "fields": {
            "phase_name": {"label": "Fase", "in_list_view": 1},
            "budget_hnl": {"label": "Presupuesto (L)", "in_list_view": 1},
            "progress_percent": {"label": "Avance físico (%)", "in_list_view": 1},
            "actual_cost_hnl": {"label": "Costo real (L)", "in_list_view": 1},
            "schedule_status": {"label": "Cronograma", "in_list_view": 1},
        },
    },
    "CC Material Ledger": {
        "title_field": "material_name",
        "search_fields": "material_name,item_code,title",
        "fields": {
            "material_name": {"label": "Material", "in_list_view": 1},
            "current_qty": {"label": "Existencia", "in_list_view": 1},
            "unit": {"label": "Unidad", "in_list_view": 1},
            "unit_cost_hnl": {"label": "Costo unitario (L)", "in_list_view": 1},
            "stock_status": {"label": "Estado", "in_list_view": 1},
        },
    },
    "CC Inventory Movement": {
        "title_field": "title",
        "search_fields": "title,material,movement_type,reference",
        "fields": {
            "posting_date": {"label": "Fecha", "in_list_view": 1},
            "material": {"label": "Material", "in_list_view": 1},
            "movement_type": {"label": "Movimiento", "in_list_view": 1},
            "quantity": {"label": "Cantidad", "in_list_view": 1},
        },
    },
    "CC Procurement Request": {
        "title_field": "title",
        "search_fields": "title,code,description",
        "fields": {
            "posting_date": {"label": "Fecha", "in_list_view": 1},
            "title": {"label": "Solicitud", "in_list_view": 1},
            "status": {"label": "Estado", "in_list_view": 1},
            "amount_hnl": {"label": "Estimado (L)", "in_list_view": 1},
        },
    },
    "CC Progress Update": {
        "title_field": "title",
        "search_fields": "title,phase,responsible,quality",
        "fields": {
            "posting_date": {"label": "Fecha", "in_list_view": 1},
            "phase": {"label": "Fase", "in_list_view": 1},
            "progress_percent": {"label": "Avance (%)", "in_list_view": 1},
            "quality": {"label": "Calidad", "in_list_view": 1},
            "responsible": {"label": "Responsable", "in_list_view": 1},
        },
    },
    "CC Weekly Closing": {
        "title_field": "title",
        "search_fields": "title,code,generated_by_name",
        "fields": {
            "week_start": {"label": "Desde", "in_list_view": 1},
            "week_end": {"label": "Hasta", "in_list_view": 1},
            "income_hnl": {"label": "Ingresos (L)", "in_list_view": 1},
            "expense_hnl": {"label": "Pagado (L)", "in_list_view": 1},
            "final_balance_hnl": {"label": "Saldo final (L)", "in_list_view": 1},
            "status": {"label": "Estado", "in_list_view": 1},
        },
    },
    "CC User Access": {
        "title_field": "display_name",
        "search_fields": "display_name,email,role_name,access_status",
        "fields": {
            "source_id": {"hidden": 1, "in_list_view": 0},
            "project": {"hidden": 1, "in_list_view": 0},
            "code": {"hidden": 1, "in_list_view": 0},
            "title": {"hidden": 1, "in_list_view": 0},
            "status": {"hidden": 1, "in_list_view": 0},
            "posting_date": {"hidden": 1, "in_list_view": 0},
            "amount_hnl": {"hidden": 1, "in_list_view": 0},
            "description": {"hidden": 1, "in_list_view": 0},
            "email": {"label": "Correo histórico", "in_list_view": 1},
            "display_name": {"label": "Nombre", "in_list_view": 1},
            "role_name": {"label": "Rol histórico", "in_list_view": 1},
            "access_status": {"label": "Estado histórico", "in_list_view": 1},
        },
    },
    "CC Audit Log": {
        "title_field": "title",
        "search_fields": "title,actor_name,actor_email,action,record_type,record_id",
        "fields": {
            "project": {"hidden": 0, "in_list_view": 0},
            "posting_date": {"label": "Fecha", "in_list_view": 1},
            "actor_name": {"label": "Usuario", "in_list_view": 1},
            "action": {"label": "Acción", "in_list_view": 1},
            "record_type": {"label": "Registro", "in_list_view": 1},
            "record_id": {"label": "Documento", "in_list_view": 1},
        },
    },
    "CC Financial Institution": {
        "title_field": "institution_name",
        "search_fields": "institution_name,short_name,code",
        "fields": {
            "institution_name": {"label": "Institución", "in_list_view": 1},
            "institution_type": {"label": "Tipo", "in_list_view": 1},
            "short_name": {"label": "Nombre corto", "in_list_view": 1},
            "is_active": {"label": "Activa", "in_list_view": 1},
        },
    },
    "CC Integration Registry": {
        "title_field": "integration_name",
        "search_fields": "integration_name,integration_code,category,provider_type",
        "fields": {
            "integration_name": {"label": "Integración", "in_list_view": 1},
            "category": {"label": "Categoría", "in_list_view": 1},
            "provider_type": {"label": "Proveedor", "in_list_view": 1},
            "enabled": {"label": "Activa", "in_list_view": 1},
            "status": {"label": "Estado", "in_list_view": 1},
        },
    },
}


def _field_rows(doctype_doc: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    standard = {str(row.fieldname): row for row in doctype_doc.fields if row.fieldname}
    custom: dict[str, Any] = {}
    for name in frappe.get_all("Custom Field", filters={"dt": doctype_doc.name}, pluck="name"):
        row = frappe.get_doc("Custom Field", name)
        custom[str(row.fieldname)] = row
    return standard, custom


def _apply_values(row: Any, values: dict[str, Any]) -> bool:
    changed = False
    for attribute, value in values.items():
        if row.get(attribute) != value:
            row.set(attribute, value)
            changed = True
    return changed


def specialize_operational_doctypes() -> None:
    """Apply compact canonical list/search metadata without deleting historical fields."""
    for doctype, specification in _SPECIALIZATIONS.items():
        if not frappe.db.exists("DocType", doctype):
            continue
        doc = frappe.get_doc("DocType", doctype)
        doc_changed = False
        for fieldname in ("title_field", "search_fields"):
            value = specification.get(fieldname)
            if doc.get(fieldname) != value:
                doc.set(fieldname, value)
                doc_changed = True
        if doc.get("show_title_field_in_link") != 1:
            doc.show_title_field_in_link = 1
            doc_changed = True

        standard, custom = _field_rows(doc)
        desired = specification.get("fields", {})
        for fieldname in _GENERIC_LIST_FIELDS:
            row = standard.get(fieldname) or custom.get(fieldname)
            if row and fieldname not in desired and row.get("in_list_view") != 0:
                row.in_list_view = 0
                if fieldname in standard:
                    doc_changed = True
                else:
                    row.save(ignore_permissions=True)

        for fieldname, values in desired.items():
            row = standard.get(fieldname) or custom.get(fieldname)
            if not row:
                continue
            changed = _apply_values(row, values)
            if changed and fieldname in standard:
                doc_changed = True
            elif changed:
                row.save(ignore_permissions=True)

        if doc_changed:
            doc.save(ignore_permissions=True)
        frappe.clear_cache(doctype=doctype)


__all__ = ["specialize_operational_doctypes"]
