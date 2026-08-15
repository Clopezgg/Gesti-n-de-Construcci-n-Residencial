from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from nexora.inventory.core import quantity
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
	previously: dict[str, Decimal] = {}
	for line in lines:
		po_line = str(line.get("purchase_order_line") or "").strip()
		if not po_line:
			raise PurchaseValidationError("Cada línea de recepción requiere referencia a línea de orden.")
		line_quantity = quantity(line.get("quantity"))
		if line_quantity <= 0:
			raise PurchaseValidationError("La cantidad recibida debe ser positiva.")
		rejected = quantity(line.get("rejected_quantity"))
		if rejected < 0:
			raise PurchaseValidationError("La cantidad rechazada no puede ser negativa.")
		net = quantity(line_quantity - rejected)
		if net < 0:
			raise PurchaseValidationError("La cantidad neta recibida no puede ser negativa.")
		received[po_line] = net
		previously[po_line] = quantity(line.get("previously_received") or 0)
	for ol in order_lines:
		po_line = str(ol.get("name") or "").strip()
		ordered_qty = quantity(ol.get("quantity"))
		if po_line in received:
			net = received[po_line]
			prior = previously.get(po_line, quantity(0))
			cumulative = quantity(prior + net)
			_min_q, max_q = tolerance_range(ordered_qty, tolerance_pct)
			if cumulative > max_q:
				raise PurchaseValidationError(
					f"La recepción de la línea {ol.get('line_code', po_line)} "
					f"excede la tolerancia máxima acumulada de {max_q} "
					f"(recibido antes: {prior}, esta recepción: {net})."
				)
	return received


def compute_po_completion_status(
	order_lines: list[Mapping[str, object]],
	received_totals: Mapping[str, Decimal],
) -> str:
	"""Determina el estado por cantidad acumulada real, no por número de recepciones."""
	for ol in order_lines:
		po_line = str(ol.get("name") or "").strip()
		ordered_qty = quantity(ol.get("quantity"))
		received = quantity(received_totals.get(po_line, 0))
		if received < ordered_qty:
			return "Sent"
	return "Completed"
