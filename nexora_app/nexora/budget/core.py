from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Final

MONEY_QUANTUM = Decimal("0.01")


def money(value: object) -> Decimal:
	try:
		d = Decimal(str(value))
	except (ValueError, TypeError, ArithmeticError):
		raise BudgetValidationError(f"Cannot convert {value!r} to Decimal")
	return d.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


BUDGET_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
	"Draft": frozenset({"Active", "Cancelled"}),
	"Active": frozenset({"Amended", "Closed"}),
	"Amended": frozenset(),
	"Closed": frozenset(),
	"Cancelled": frozenset(),
}

TERMINAL_STATES: Final[frozenset[str]] = frozenset({"Amended", "Closed", "Cancelled"})


class BudgetValidationError(ValueError):
	...


class OverspendError(BudgetValidationError):
	...


class InvalidTransition(BudgetValidationError):
	...


class InvalidLineError(BudgetValidationError):
	...


def assert_transition(current: str, target: str) -> None:
	allowed = BUDGET_TRANSITIONS.get(current)
	if allowed is None or target not in allowed:
		raise InvalidTransition(f"No se permite transici�n de {current} a {target}")


def compute_line_balances(
	approved: Decimal | str | float,
	committed: Decimal | str | float,
	executed: Decimal | str | float,
) -> dict[str, Decimal]:
	a = money(approved)
	c = money(committed)
	e = money(executed)
	return {
		"approved_hnl": a,
		"committed_hnl": c,
		"executed_hnl": e,
		"available_hnl": money(a - c - e),
	}


def compute_budget_totals(
	lines: list[dict[str, Decimal | str | float]],
) -> dict[str, Decimal]:
	total_approved = Decimal(0)
	total_committed = Decimal(0)
	total_executed = Decimal(0)
	total_available = Decimal(0)
	for line in lines:
		bal = compute_line_balances(
			line.get("approved_hnl", 0),
			line.get("committed_hnl", 0),
			line.get("executed_hnl", 0),
		)
		total_approved += bal["approved_hnl"]
		total_committed += bal["committed_hnl"]
		total_executed += bal["executed_hnl"]
		total_available += bal["available_hnl"]
	return {
		"total_approved_hnl": money(total_approved),
		"total_committed_hnl": money(total_committed),
		"total_executed_hnl": money(total_executed),
		"total_available_hnl": money(total_available),
	}


def validate_no_overspend(
	approved: Decimal | str | float,
	committed: Decimal | str | float,
	executed: Decimal | str | float,
	additional: Decimal | str | float = Decimal(0),
) -> None:
	bal = compute_line_balances(approved, committed, executed)
	available = bal["available_hnl"]
	add = money(additional)
	if add > available:
		raise OverspendError(
			f"Compromiso de {add} excede disponible {bal['available_hnl']} "
			f"(aprobado={bal['approved_hnl']}, comprometido={bal['committed_hnl']}, "
			f"ejecutado={bal['executed_hnl']})"
		)


def validate_line_amount(approved: Decimal | str | float) -> Decimal:
	amt = money(approved)
	if amt <= 0:
		raise InvalidLineError(f"El monto aprobado debe ser positivo, no {amt}")
	return amt
