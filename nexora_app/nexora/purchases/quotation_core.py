from __future__ import annotations

QUOTATION_TRANSITIONS = {
	"Draft": frozenset({"Submitted", "Cancelled"}),
	"Submitted": frozenset({"Accepted", "Rejected", "Expired", "Cancelled"}),
	"Accepted": frozenset({"Cancelled"}),
	"Rejected": frozenset({"Cancelled"}),
	"Expired": frozenset(),
	"Cancelled": frozenset(),
}


def assert_quotation_transition(source: str, target: str) -> None:
	if source == target:
		return
	if target not in QUOTATION_TRANSITIONS.get(source, frozenset()):
		raise ValueError(f"Transición no permitida: {source} → {target}.")
