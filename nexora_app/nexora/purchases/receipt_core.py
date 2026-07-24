from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from nexora.purchases.order_core import tolerance_range
from nexora.purchases.request_core import PurchaseValidationError, money

GOODS_RECEIPT_TRANSITIONS = {
	"Draft": frozenset({"Completed", "Cancelled"}),
	"Completed": frozenset(),
	"Cancelled": frozenset(),
}


def assert_receipt_transition(source: str, target: str) -> None:
	if source == target:
		return
	if target not in GOODS_RECEIPT_TRANSITIONS.get(source, frozenset()):
		raise PurchaseValidationError(f"Transición de recepción no permitida: {source} → {target}.")


def validate_receipt_lines(
	lines: list[Mapping[str, object]],
	order_lines: list[Mapping[str, object]],
	tolerance_pct: Decimal | None = None,
) -> dict[str, Decimal]:
	received: dict[str, Decimal] = {}
	for line in lines:
		po_line = str(line.get("purchase_order_line") or "").strip()
		if not po_line:
			raise PurchaseValidationError("Cada línea de recepción requiere referencia a línea de orden.")
		quantity = money(line.get("quantity"))
		if quantity <= 0:
			raise PurchaseValidationError("La cantidad recibida debe ser positiva.")
		rejected = money(line.get("rejected_quantity"))
		if rejected < 0:
			raise PurchaseValidationError("La cantidad rechazada no puede ser negativa.")
		net = money(quantity - rejected)
		if net < 0:
			raise PurchaseValidationError("La cantidad neta recibida no puede ser negativa.")
		received[po_line] = net
	for ol in order_lines:
		po_line = str(ol.get("name") or "").strip()
		ordered_qty = money(ol.get("quantity"))
		if po_line in received:
			net = received[po_line]
			_min_q, max_q = tolerance_range(ordered_qty, tolerance_pct)
			if net > max_q:
				raise PurchaseValidationError(
					f"La recepción de la línea {ol.get('line_code', po_line)} "
					f"excede la tolerancia máxima de {max_q}."
				)
	return received
