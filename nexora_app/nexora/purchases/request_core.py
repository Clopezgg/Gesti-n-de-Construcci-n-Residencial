from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable, Mapping

try:
	from frappe.exceptions import ValidationError as FrappeValidationError
except ImportError:
	FrappeValidationError = Exception


class PurchaseValidationError(ValueError, FrappeValidationError):
	"""Error de dominio utilizable dentro y fuera de Frappe."""


MONEY = Decimal("0.01")
PURCHASE_REQUEST_TRANSITIONS = {
	"Draft": frozenset({"In Review", "Cancelled"}),
	"In Review": frozenset({"Draft", "Approved", "Rejected", "Cancelled"}),
	"Approved": frozenset({"Cancelled"}),
	"Rejected": frozenset(),
	"Cancelled": frozenset(),
}
PURCHASE_PRIORITIES = frozenset({"Low", "Normal", "High", "Urgent"})
PURCHASE_ITEM_TYPES = frozenset({"Goods", "Service"})


def money(value: object) -> Decimal:
	try:
		return Decimal(str(value or 0)).quantize(MONEY, rounding=ROUND_HALF_UP)
	except Exception as exc:
		raise PurchaseValidationError("El importe de compra no es válido.") from exc


def assert_request_transition(source: str, target: str) -> None:
	if source == target:
		return
	if target not in PURCHASE_REQUEST_TRANSITIONS.get(source, frozenset()):
		raise PurchaseValidationError(f"Transición no permitida: {source} → {target}.")


def validate_request_dates(request_date: object, required_by: object) -> None:
	if not request_date or not required_by:
		raise PurchaseValidationError("La solicitud requiere fecha de solicitud y fecha requerida.")
	if date.fromisoformat(str(required_by)) < date.fromisoformat(str(request_date)):
		raise PurchaseValidationError("La fecha requerida no puede ser anterior a la solicitud.")


@dataclass(frozen=True)
class PurchaseRequestAmounts:
	total: Decimal
	line_count: int


def request_line_amounts(lines: Iterable[Mapping[str, object]]) -> PurchaseRequestAmounts:
	total = Decimal("0")
	seen: set[str] = set()
	count = 0
	for index, line in enumerate(lines, start=1):
		line_code = str(line.get("line_code") or index).strip()
		if not line_code:
			raise PurchaseValidationError("Cada línea requiere un código.")
		if line_code in seen:
			raise PurchaseValidationError(f"La línea de solicitud {line_code} está duplicada.")
		seen.add(line_code)
		item_type = str(line.get("item_type") or "Goods").strip().title()
		if item_type not in PURCHASE_ITEM_TYPES:
			raise PurchaseValidationError("El tipo de línea debe ser Goods o Service.")
		if not str(line.get("description") or "").strip():
			raise PurchaseValidationError(f"La línea {line_code} requiere descripción.")
		if not str(line.get("uom") or "").strip():
			raise PurchaseValidationError(f"La línea {line_code} requiere unidad de medida.")
		if not str(line.get("economic_category") or "").strip():
			raise PurchaseValidationError(f"La línea {line_code} requiere clasificación económica.")
		quantity = money(line.get("quantity"))
		unit_rate = money(line.get("estimated_unit_rate"))
		if quantity <= 0:
			raise PurchaseValidationError(f"La línea {line_code} requiere cantidad positiva.")
		if unit_rate < 0:
			raise PurchaseValidationError(f"La línea {line_code} no admite precio negativo.")
		expected = money(quantity * unit_rate)
		amount = money(line.get("estimated_amount") if line.get("estimated_amount") is not None else expected)
		if amount != expected:
			raise PurchaseValidationError(
				f"El importe estimado de la línea {line_code} no coincide con cantidad por precio."
			)
		total += amount
		count += 1
	if not count:
		raise PurchaseValidationError("La solicitud de compra requiere al menos una línea.")
	return PurchaseRequestAmounts(money(total), count)
