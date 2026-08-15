from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from nexora.inventory.service import create_stock_transaction, transition_stock_transaction
from nexora.purchases.request_core import money


def _goods_lines(receipt: Any, transaction_type: str) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for line in receipt.lines:
        if str(line.item_type or "").strip().title() != "Goods":
            continue
        if not line.catalog_item:
            frappe.throw(_("La línea {0} de la recepción requiere un artículo de inventario.").format(line.line_code))
        quantity = money(line.accepted_quantity)
        if quantity <= 0:
            continue
        lines.append(
            {
                "line_code": str(line.line_code or "001"),
                "item": line.catalog_item,
                "warehouse": receipt.warehouse,
                "quantity": str(quantity),
                "unit_rate": str(line.unit_rate),
                "amount": str(line.amount),
                "reference_doctype": "NXR Goods Receipt",
                "reference_name": receipt.name,
                "notes": f"Recepción {receipt.document_number} · {transaction_type}",
            }
        )
    return lines


def _stock_transaction_names(receipt_name: str) -> list[str]:
    return frappe.get_all(
        "NXR Stock Transaction",
        filters={"goods_receipt": receipt_name},
        pluck="name",
        limit_page_length=50,
    )


def sync_goods_receipt_inventory(doc: Any, method: str | None = None) -> None:
    if doc.status not in {"Completed", "Cancelled"}:
        return
    if not doc.warehouse:
        frappe.throw(_("La recepción requiere una bodega destino antes de completarse."))

    existing = _stock_transaction_names(doc.name)
    if doc.status == "Completed" and existing:
        return
    if doc.status == "Cancelled":
        if any(frappe.db.get_value("NXR Stock Transaction", name, "transaction_type") == "Return" for name in existing):
            return
        source_type = "Return"
    else:
        source_type = "Receipt"

    lines = _goods_lines(doc, source_type)
    if not lines:
        return
    create_result = create_stock_transaction(
        {
            "idempotency_key": f"goods-receipt-stock:create:{doc.name}:{source_type}",
            "transaction_type": source_type,
            "project": doc.project,
            "warehouse": doc.warehouse,
            "transaction_date": doc.receipt_date,
            "notes": f"{source_type} generado desde recepción {doc.document_number}",
            "lines": lines,
            "evidence": doc.evidence,
            "purchase_order": doc.purchase_order,
            "goods_receipt": doc.name,
        }
    )
    transition_stock_transaction(
        transaction=create_result["name"],
        status="Completed",
        idempotency_key=f"goods-receipt-stock:complete:{doc.name}:{source_type}",
        reason=f"Sincronización automática de recepción {doc.document_number}",
    )
