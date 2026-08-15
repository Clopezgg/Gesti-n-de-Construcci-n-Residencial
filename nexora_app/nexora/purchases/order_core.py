from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal

from nexora.inventory.core import quantity
from nexora.purchases.request_core import PurchaseValidationError, money

PURCHASE_ORDER_TRANSITIONS = {
	"Draft": frozenset({"Confirmed", "Cancelled"}),
	"Confirmed": frozenset({"Approved", "Cancelled"}),
	"Approved": frozenset({"Sent", "Cancelled"}),
	"Sent": frozenset({"Completed", "Cancelled"}),
	"Completed": frozenset(),
	"Cancelled": frozenset(),
}
DEFAULT_TOLERANCE_PERCENTAGE = Decimal(10)


def assert_order_transition(source: str, target: str) -> None:
	if source == target:
		return
	if target not in PURCHASE_ORDER_TRANSITIONS.get(source, frozenset()):
		raise PurchaseValidationError(f"Transición de orden no permitida: {source} → {target}.")


@dataclass(frozen=True)
class OrderLineAmounts:
	amount: Decimal
	tax_amount: Decimal
	discount_amount: Decimal
	net_amount: Decimal
	total: Decimal


def order_line_amounts(lines: Iterable[Mapping[str, object]]) -> list[OrderLineAmounts]:
	result: list[OrderLineAmounts] = []
	for line in lines:
		line_quantity = quantity(line.get("quantity"))
		if line_quantity <= 0:
			raise PurchaseValidationError("Cada línea de orden requiere cantidad positiva.")
		unit_rate = money(line.get("unit_rate"))
		if unit_rate < 0:
			raise PurchaseValidationError("Cada línea de orden requiere precio unitario no negativo.")
		amount = money(line_quantity * unit_rate)
		charge_amount = money(line.get("charge_amount"))
		tax_rate = money(line.get("tax_rate"))
		tax_amount = money(amount * tax_rate / 100) if tax_rate else money(line.get("tax_amount"))
		discount_rate = money(line.get("discount_rate"))
		discount_amount = (
			money(amount * discount_rate / 100) if discount_rate else money(line.get("discount_amount"))
		)
		net_amount = money(amount + charge_amount + tax_amount - discount_amount)
		if net_amount < 0:
			raise PurchaseValidationError("El importe neto de línea no puede ser negativo.")
		result.append(OrderLineAmounts(amount, tax_amount, discount_amount, net_amount, net_amount))
	if not result:
		raise PurchaseValidationError("La orden de compra requiere al menos una línea.")
	return result


def tolerance_range(ordered: Decimal, tolerance_pct: Decimal | None = None) -> tuple[Decimal, Decimal]:
	pct = tolerance_pct if tolerance_pct is not None else DEFAULT_TOLERANCE_PERCENTAGE
	factor = pct / 100
	min_qty = quantity(ordered * (1 - factor))
	max_qty = quantity(ordered * (1 + factor))
	return min_qty, max_qty
