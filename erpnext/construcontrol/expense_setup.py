from __future__ import annotations

from typing import Any

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def _exclude_standard_fields(
    definitions: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """Do not recreate fields that already belong to the base DocType schema.

    ``create_custom_fields(update=True)`` updates existing Custom Field records,
    but Frappe correctly rejects a Custom Field whose name already exists as a
    standard DocField. Runtime definitions already include fields such as
    ``supplier`` and ``due_date`` on CC Payable Control, so they must be reused
    rather than created a second time.
    """
    filtered: dict[str, list[dict[str, Any]]] = {}
    for doctype, fields in definitions.items():
        standard_fields = set(
            frappe.get_all(
                "DocField",
                filters={"parent": doctype},
                pluck="fieldname",
            )
        )
        skipped = [
            str(field.get("fieldname") or "")
            for field in fields
            if field.get("fieldname") in standard_fields
        ]
        filtered[doctype] = [
            field for field in fields if field.get("fieldname") not in standard_fields
        ]
        if skipped:
            print(
                f"[ConstruControl] reusing standard fields on {doctype}: "
                + ", ".join(sorted(skipped)),
                flush=True,
            )
    return filtered


def ensure_expense_fields() -> None:
    definitions: dict[str, list[dict[str, Any]]] = {
        "CC Expense Control": [
            {"fieldname": "invoice_section", "label": "Factura y orden de compra", "fieldtype": "Section Break", "insert_after": "provider_name"},
            {"fieldname": "invoice_number", "label": "Número de factura", "fieldtype": "Data", "in_list_view": 1, "insert_after": "invoice_section"},
            {"fieldname": "invoice_date", "label": "Fecha de factura", "fieldtype": "Date", "insert_after": "invoice_number"},
            {"fieldname": "due_date", "label": "Fecha de vencimiento", "fieldtype": "Date", "in_list_view": 1, "insert_after": "invoice_date"},
            {"fieldname": "purchase_order_reference", "label": "Orden de compra", "fieldtype": "Data", "insert_after": "due_date"},
            {"fieldname": "cost_center", "label": "Centro de costo", "fieldtype": "Link", "options": "Cost Center", "insert_after": "purchase_order_reference"},
            {"fieldname": "invoice_attachment", "label": "Factura o recibo", "fieldtype": "Attach", "insert_after": "cost_center"},
            {"fieldname": "amount_breakdown_section", "label": "Desglose financiero", "fieldtype": "Section Break", "insert_after": "invoice_attachment"},
            {"fieldname": "subtotal_hnl", "label": "Subtotal (L)", "fieldtype": "Currency", "options": "HNL", "insert_after": "amount_breakdown_section"},
            {"fieldname": "tax_hnl", "label": "Impuestos (L)", "fieldtype": "Currency", "options": "HNL", "default": "0", "insert_after": "subtotal_hnl"},
            {"fieldname": "withholding_hnl", "label": "Retenciones (L)", "fieldtype": "Currency", "options": "HNL", "default": "0", "insert_after": "tax_hnl"},
            {"fieldname": "discount_hnl", "label": "Descuentos (L)", "fieldtype": "Currency", "options": "HNL", "default": "0", "insert_after": "withholding_hnl"},
            {"fieldname": "calculated_total_hnl", "label": "Total calculado (L)", "fieldtype": "Currency", "options": "HNL", "read_only": 1, "insert_after": "discount_hnl"},
            {"fieldname": "payment_control_section", "label": "Pago y cuenta por pagar", "fieldtype": "Section Break", "insert_after": "calculated_total_hnl"},
            {"fieldname": "payment_status", "label": "Estado de pago", "fieldtype": "Select", "options": "draft\npending_approval\napproved\npartially_paid\npaid\noverdue\ncancelled\nreimbursed", "default": "draft", "in_list_view": 1, "insert_after": "payment_control_section"},
            {"fieldname": "approved_amount_hnl", "label": "Monto aprobado (L)", "fieldtype": "Currency", "options": "HNL", "read_only": 1, "insert_after": "payment_status"},
            {"fieldname": "paid_amount_hnl", "label": "Pagado (L)", "fieldtype": "Currency", "options": "HNL", "default": "0", "in_list_view": 1, "insert_after": "approved_amount_hnl"},
            {"fieldname": "balance_due_hnl", "label": "Saldo pendiente (L)", "fieldtype": "Currency", "options": "HNL", "read_only": 1, "in_list_view": 1, "insert_after": "paid_amount_hnl"},
            {"fieldname": "payment_reference", "label": "Referencia de pago", "fieldtype": "Data", "insert_after": "balance_due_hnl"},
            {"fieldname": "payment_date", "label": "Fecha de pago", "fieldtype": "Date", "insert_after": "payment_reference"},
            {"fieldname": "payment_evidence", "label": "Comprobante de pago", "fieldtype": "Attach", "insert_after": "payment_date"},
            {"fieldname": "professional_approval_status", "label": "Aprobación", "fieldtype": "Select", "options": "draft\npending\napproved\nrejected", "default": "draft", "in_list_view": 1, "insert_after": "payment_evidence"},
            {"fieldname": "approved_by_user", "label": "Aprobado por", "fieldtype": "Link", "options": "User", "read_only": 1, "insert_after": "professional_approval_status"},
            {"fieldname": "approved_at", "label": "Fecha de aprobación", "fieldtype": "Datetime", "read_only": 1, "insert_after": "approved_by_user"},
            {"fieldname": "rejection_reason", "label": "Motivo de rechazo", "fieldtype": "Small Text", "insert_after": "approved_at"},
        ],
        "CC Payable Control": [
            {"fieldname": "expense_control", "label": "Gasto relacionado", "fieldtype": "Link", "options": "CC Expense Control", "unique": 1, "in_list_view": 1, "insert_after": "description"},
            {"fieldname": "supplier", "label": "Proveedor", "fieldtype": "Link", "options": "Supplier", "in_list_view": 1, "insert_after": "expense_control"},
            {"fieldname": "provider_name", "label": "Nombre del proveedor", "fieldtype": "Data", "in_list_view": 1, "insert_after": "supplier"},
            {"fieldname": "invoice_number", "label": "Factura", "fieldtype": "Data", "in_list_view": 1, "insert_after": "provider_name"},
            {"fieldname": "due_date", "label": "Vencimiento", "fieldtype": "Date", "in_list_view": 1, "insert_after": "invoice_number"},
            {"fieldname": "original_amount_hnl", "label": "Monto original (L)", "fieldtype": "Currency", "options": "HNL", "insert_after": "due_date"},
            {"fieldname": "paid_amount_hnl", "label": "Pagado (L)", "fieldtype": "Currency", "options": "HNL", "insert_after": "original_amount_hnl"},
            {"fieldname": "balance_due_hnl", "label": "Saldo (L)", "fieldtype": "Currency", "options": "HNL", "in_list_view": 1, "insert_after": "paid_amount_hnl"},
            {"fieldname": "payable_status", "label": "Estado", "fieldtype": "Select", "options": "pending\npartial\npaid\noverdue\ncancelled\nreimbursed", "in_list_view": 1, "insert_after": "balance_due_hnl"},
        ],
    }
    create_custom_fields(_exclude_standard_fields(definitions), update=True)
    frappe.clear_cache(doctype="CC Expense Control")
    frappe.clear_cache(doctype="CC Payable Control")


__all__ = ["ensure_expense_fields"]
