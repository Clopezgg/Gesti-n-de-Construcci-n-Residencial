from __future__ import annotations

from collections.abc import Mapping

CLOSE_TRANSITIONS = {
	"Draft": frozenset({"In Review", "Cancelled"}),
	"In Review": frozenset({"Approved", "Rejected"}),
	"Approved": frozenset(),
	"Rejected": frozenset({"Draft"}),
	"Cancelled": frozenset(),
}
TERMINAL_STATES = frozenset({"Approved", "Cancelled"})


class CloseValidationError(ValueError):
	pass


class InvalidTransition(CloseValidationError):
	pass


class ReconciliationError(CloseValidationError):
	pass


def assert_transition(current: str, target: str) -> None:
	if current not in CLOSE_TRANSITIONS:
		raise InvalidTransition(f"Estado de cierre desconocido: {current}")
	allowed = CLOSE_TRANSITIONS[current]
	if target not in allowed:
		raise InvalidTransition(f"Transicion invalida: {current} -> {target}")


def reconcile(before: Mapping[str, object], after: Mapping[str, object]) -> dict[str, object]:
	mismatches = {}
	for key in before:
		if before[key] != after.get(key):
			mismatches[key] = {"before": before[key], "after": after.get(key)}
	if mismatches:
		raise ReconciliationError(f"Discrepancia en reconciliacion: {mismatches}")
	return dict(before)
