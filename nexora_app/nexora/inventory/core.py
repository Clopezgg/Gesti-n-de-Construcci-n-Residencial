from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from nexora.purchases.request_core import PurchaseValidationError

STOCK_TRANSACTION_TYPES = frozenset(
	{
		"Receipt",
		"Transfer In",
		"Transfer Out",
		"Issue to Contractor",
		"Consumption",
		"Return",
		"Damage",
		"Loss",
		"Adjustment",
		"Physical Count",
	}
)
STOCK_TRANSACTION_TRANSITIONS = {
	"Draft": frozenset({"Completed", "Cancelled"}),
	"Completed": frozenset(),
	"Cancelled": frozenset(),
}

# Misma clasificación de dirección que ya usa `dashboard/inventory_query.py`
# (`critical_inventory`) para calcular el saldo real por ítem/bodega: entra
# con signo positivo, sale con signo negativo. `Adjustment`/`Physical Count`
# quedan fuera a propósito, igual que en esa consulta: no representan una
# entrada o salida de cantidad conocida, sino un recuento que corrige el
# saldo existente, y validarlos como salida rechazaría un ajuste legítimo
# que solo corrige un conteo equivocado.
INCOMING_STOCK_TRANSACTION_TYPES = frozenset({"Receipt", "Transfer In", "Return"})
OUTGOING_STOCK_TRANSACTION_TYPES = frozenset(
	{"Transfer Out", "Issue to Contractor", "Consumption", "Damage", "Loss"}
)


def money(value: object) -> Decimal:
	try:
		return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
	except Exception as exc:
		raise PurchaseValidationError("El importe de inventario no es válido.") from exc


def quantity(value: object) -> Decimal:
	try:
		return Decimal(str(value or 0)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
	except Exception as exc:
		raise PurchaseValidationError("La cantidad de inventario no es válida.") from exc


def assert_stock_transition(source: str, target: str) -> None:
	if source == target:
		return
	if target not in STOCK_TRANSACTION_TRANSITIONS.get(source, frozenset()):
		raise PurchaseValidationError(f"Transición de inventario no permitida: {source} → {target}.")


def validate_item_balance(item: str, warehouse: str, current_qty: Decimal, outgoing_qty: Decimal) -> None:
	balance = quantity(current_qty - outgoing_qty)
	if balance < 0:
		raise PurchaseValidationError(
			f"El item {item} en bodega {warehouse} quedaría con inventario negativo ({balance})."
		)


class StockBalance:
	def __init__(self) -> None:
		self._lines: dict[tuple[str, str], Decimal] = {}

	def add(self, item: str, warehouse: str, qty: Decimal) -> None:
		key = (item, warehouse)
		current = self._lines.get(key, Decimal(0))
		self._lines[key] = quantity(current + qty)

	def remove(self, item: str, warehouse: str, qty: Decimal) -> Decimal:
		key = (item, warehouse)
		current = self._lines.get(key, Decimal(0))
		if current < qty:
			raise PurchaseValidationError(f"Saldo insuficiente de {item} en {warehouse}: {current} < {qty}")
		remaining = quantity(current - qty)
		self._lines[key] = remaining
		return remaining

	def balance(self, item: str, warehouse: str) -> Decimal:
		return self._lines.get((item, warehouse), Decimal(0))
