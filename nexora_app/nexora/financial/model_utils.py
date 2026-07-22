from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import frappe

MONEY_QUANTUM = Decimal("0.01")
RATE_QUANTUM = Decimal("0.000000001")


def money(value: object) -> Decimal:
    try:
        result = Decimal(str(value or 0)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        frappe.throw(f"Importe inválido: {value!r}")
        raise exc
    return result


def rate(value: object) -> Decimal:
    try:
        result = Decimal(str(value or 0)).quantize(RATE_QUANTUM, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        frappe.throw(f"Tasa inválida: {value!r}")
        raise exc
    return result


def validate_immutable(doc, fieldnames: tuple[str, ...]) -> None:
    if doc.is_new():
        return
    previous = doc.get_doc_before_save()
    if not previous:
        return
    changed = [fieldname for fieldname in fieldnames if doc.get(fieldname) != previous.get(fieldname)]
    if changed:
        frappe.throw(f"Documento inmutable; campos alterados: {', '.join(changed)}")


def validate_document_number(value: str | None) -> None:
    if value and (len(value) != 12 or not value.isdigit()):
        frappe.throw("El número documental debe contener exactamente 12 dígitos.")
