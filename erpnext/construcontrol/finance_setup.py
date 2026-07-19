from __future__ import annotations

import json
from typing import Any

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

_INSTITUTIONS: tuple[dict[str, Any], ...] = (
    {"code": "ATLANTIDA", "institution_name": "Banco Atlántida", "short_name": "Atlántida", "institution_type": "bank", "brand_color": "#C8202F", "supports_remittance": 1, "supports_deposit": 1, "supports_transfer": 1, "sort_order": 10},
    {"code": "BANPAIS", "institution_name": "Banco del País", "short_name": "Banpaís", "institution_type": "bank", "brand_color": "#00529B", "supports_remittance": 1, "supports_deposit": 1, "supports_transfer": 1, "sort_order": 20},
    {"code": "BAC", "institution_name": "BAC Credomatic", "short_name": "BAC", "institution_type": "bank", "brand_color": "#D71920", "supports_remittance": 1, "supports_deposit": 1, "supports_transfer": 1, "sort_order": 30},
    {"code": "FICOHSA", "institution_name": "Banco Ficohsa", "short_name": "Ficohsa", "institution_type": "bank", "brand_color": "#C41230", "supports_remittance": 1, "supports_deposit": 1, "supports_transfer": 1, "sort_order": 40},
    {"code": "DAVIVIENDA", "institution_name": "Banco Davivienda", "short_name": "Davivienda", "institution_type": "bank", "brand_color": "#E1261C", "supports_remittance": 1, "supports_deposit": 1, "supports_transfer": 1, "sort_order": 50},
    {"code": "OCCIDENTE", "institution_name": "Banco de Occidente", "short_name": "Occidente", "institution_type": "bank", "brand_color": "#1F6B3B", "supports_remittance": 1, "supports_deposit": 1, "supports_transfer": 1, "sort_order": 60},
    {"code": "BANRURAL", "institution_name": "Banrural Honduras", "short_name": "Banrural", "institution_type": "bank", "brand_color": "#168447", "supports_remittance": 1, "supports_deposit": 1, "supports_transfer": 1, "sort_order": 70},
    {"code": "WESTERN_UNION", "institution_name": "Western Union", "short_name": "Western Union", "institution_type": "remittance", "brand_color": "#111111", "supports_remittance": 1, "sort_order": 80},
    {"code": "MONEYGRAM", "institution_name": "MoneyGram", "short_name": "MoneyGram", "institution_type": "remittance", "brand_color": "#E31B23", "supports_remittance": 1, "sort_order": 90},
    {"code": "INTERMEX", "institution_name": "Intermex", "short_name": "Intermex", "institution_type": "remittance", "brand_color": "#1D4F91", "supports_remittance": 1, "sort_order": 100},
    {"code": "CASH", "institution_name": "Efectivo", "short_name": "Efectivo", "institution_type": "cash", "brand_color": "#175C4C", "supports_deposit": 1, "sort_order": 110},
)


def ensure_finance_fields() -> None:
    create_custom_fields(
        {
            "CC Funding Source": [
                {"fieldname": "treasury_section", "label": "Tesorería y origen del dinero", "fieldtype": "Section Break", "insert_after": "income_type"},
                {"fieldname": "transaction_channel", "label": "Canal", "fieldtype": "Select", "options": "remittance\ndeposit\ntransfer\ncash\nother", "reqd": 1, "default": "remittance", "in_list_view": 1, "insert_after": "treasury_section"},
                {"fieldname": "financial_institution", "label": "Banco o remesadora", "fieldtype": "Link", "options": "CC Financial Institution", "in_list_view": 1, "insert_after": "transaction_channel"},
                {"fieldname": "institution_brand_html", "label": "Institución seleccionada", "fieldtype": "HTML", "insert_after": "financial_institution"},
                {"fieldname": "beneficiary", "label": "Beneficiario", "fieldtype": "Data", "insert_after": "institution_brand_html"},
                {"fieldname": "account_reference", "label": "Cuenta receptora", "fieldtype": "Data", "insert_after": "beneficiary"},
                {"fieldname": "transaction_reference", "label": "Referencia de operación", "fieldtype": "Data", "in_list_view": 1, "insert_after": "account_reference"},
                {"fieldname": "amounts_section", "label": "Conversión y monto neto", "fieldtype": "Section Break", "insert_after": "transaction_reference"},
                {"fieldname": "gross_amount", "label": "Monto bruto", "fieldtype": "Currency", "options": "original_currency", "insert_after": "amounts_section"},
                {"fieldname": "fee_amount", "label": "Comisión", "fieldtype": "Currency", "options": "original_currency", "default": "0", "insert_after": "gross_amount"},
                {"fieldname": "net_amount", "label": "Monto neto", "fieldtype": "Currency", "options": "original_currency", "read_only": 1, "insert_after": "fee_amount"},
                {"fieldname": "original_currency", "label": "Moneda original", "fieldtype": "Link", "options": "Currency", "default": "HNL", "insert_after": "net_amount"},
                {"fieldname": "treasury_exchange_rate", "label": "Tipo de cambio a HNL", "fieldtype": "Float", "precision": "6", "default": "1", "insert_after": "original_currency"},
                {"fieldname": "net_amount_hnl", "label": "Neto recibido (L)", "fieldtype": "Currency", "options": "HNL", "read_only": 1, "insert_after": "treasury_exchange_rate"},
                {"fieldname": "conciliation_section", "label": "Conciliación y destino", "fieldtype": "Section Break", "insert_after": "net_amount_hnl"},
                {"fieldname": "reconciliation_status", "label": "Conciliación", "fieldtype": "Select", "options": "pending\nverified\nreconciled\nrejected", "default": "pending", "in_list_view": 1, "insert_after": "conciliation_section"},
                {"fieldname": "purpose", "label": "Destino del dinero", "fieldtype": "Small Text", "insert_after": "reconciliation_status"},
                {"fieldname": "receipt_number", "label": "Número de comprobante", "fieldtype": "Data", "insert_after": "purpose"},
                {"fieldname": "treasury_evidence", "label": "Comprobante", "fieldtype": "Attach", "insert_after": "receipt_number"},
            ]
        },
        update=True,
    )


def seed_financial_institutions() -> None:
    if not frappe.db.exists("DocType", "CC Financial Institution"):
        return
    for values in _INSTITUTIONS:
        code = str(values["code"])
        source_key = f"financial-institution:{code.casefold()}"
        name = frappe.db.get_value("CC Financial Institution", {"code": code}, "name")
        doc = frappe.get_doc("CC Financial Institution", name) if name else frappe.new_doc("CC Financial Institution")
        doc.code = code
        doc.source_key = source_key
        doc.source_id = code
        for fieldname, value in values.items():
            doc.set(fieldname, value)
        doc.country = "Honduras"
        doc.is_active = 1
        doc.is_protected = 1
        doc.is_logically_deleted = 0
        doc.payload_json = json.dumps({"seed": "ConstruControl", "code": code}, sort_keys=True)
        if doc.is_new():
            doc.insert(ignore_permissions=True)
        else:
            doc.save(ignore_permissions=True)


def ensure_finance_configuration() -> None:
    ensure_finance_fields()
    seed_financial_institutions()
    frappe.clear_cache(doctype="CC Funding Source")
    frappe.clear_cache(doctype="CC Financial Institution")


__all__ = ["ensure_finance_configuration", "ensure_finance_fields", "seed_financial_institutions"]
