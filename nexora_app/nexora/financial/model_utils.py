from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

import frappe
from frappe import _

MONEY_QUANTUM = Decimal("0.01")
RATE_QUANTUM = Decimal("0.000000001")


def money(value: object) -> Decimal:
	try:
		result = Decimal(str(value or 0)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
	except (InvalidOperation, ValueError):
		frappe.throw(_("Importe inválido: {0}").format(repr(value)))
	return result


def rate(value: object) -> Decimal:
	try:
		result = Decimal(str(value or 0)).quantize(RATE_QUANTUM, rounding=ROUND_HALF_UP)
	except (InvalidOperation, ValueError):
		frappe.throw(_("Tasa inválida: {0}").format(repr(value)))
	return result


def validate_immutable(doc, fieldnames: tuple[str, ...]) -> None:
	if doc.is_new():
		return
	previous = doc.get_doc_before_save()
	if not previous:
		return
	changed = [fieldname for fieldname in fieldnames if doc.get(fieldname) != previous.get(fieldname)]
	if changed:
		frappe.throw(_("Documento inmutable; campos alterados: {0}").format(", ".join(changed)))


def validate_document_number(value: str | None) -> None:
	if value and (len(value) != 12 or not value.isdigit()):
		frappe.throw(_("El número documental debe contener exactamente 12 dígitos."))
