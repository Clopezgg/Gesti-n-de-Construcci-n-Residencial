from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from decimal import InvalidOperation as DecimalInvalidOperation
from typing import Final

MONEY_QUANTUM = Decimal("0.01")

PROGRESS_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
	"Draft": frozenset({"Submitted", "Cancelled"}),
	"Submitted": frozenset({"Approved", "Rejected"}),
	"Approved": frozenset({"Corrected"}),
	"Corrected": frozenset({"Approved"}),
	"Rejected": frozenset({"Corrected"}),
	"Cancelled": frozenset(),
}

TERMINAL_STATES: Final[frozenset[str]] = frozenset({"Cancelled"})


class ProgressValidationError(ValueError): ...


class InvalidTransition(ProgressValidationError): ...


def assert_transition(current: str, target: str) -> None:
	allowed = PROGRESS_TRANSITIONS.get(current)
	if allowed is None or target not in allowed:
		raise InvalidTransition(f"No se permite transición de {current} a {target}")


def money(value: object) -> Decimal:
	try:
		return Decimal(str(value or 0)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
	except (DecimalInvalidOperation, ValueError, TypeError) as exc:
		raise ProgressValidationError(f"Importe inválido: {value!r}") from exc


def progress_percent(value: object) -> Decimal:
	try:
		pct = Decimal(str(value or 0))
	except (DecimalInvalidOperation, ValueError, TypeError) as exc:
		raise ProgressValidationError(f"Porcentaje inválido: {value!r}") from exc
	if pct < 0 or pct > 100:
		raise ProgressValidationError(f"El porcentaje debe estar entre 0 y 100, no {pct}")
	return pct
