from __future__ import annotations

from collections.abc import Mapping

SUPPLIER_PROFILE_TRANSITIONS = {
	"Draft": frozenset({"Active", "Inactive"}),
	"Active": frozenset({"Suspended", "Expired", "Inactive"}),
	"Suspended": frozenset({"Active", "Expired", "Inactive"}),
	"Expired": frozenset({"Active", "Inactive"}),
	"Inactive": frozenset(),
}

SUPPLIER_CLASSIFICATIONS = frozenset({"Goods", "Services", "Mixed", "Consultant", "Logistics", "Other"})
ACTIVE_COMPLIANCE_STATES = frozenset({"Current", "Approved Exception"})


def normalize_classification(value: object) -> str:
	classification = str(value or "Other").strip().title()
	if classification not in SUPPLIER_CLASSIFICATIONS:
		raise ValueError("La clasificación de proveedor no está permitida.")
	return classification


def assert_transition(source: str, target: str, transitions: Mapping[str, frozenset[str]]) -> None:
	if source == target:
		return
	if source not in transitions or target not in transitions:
		raise ValueError("Estado de proveedor desconocido.")
	if target not in transitions[source]:
		raise ValueError(f"Transición no permitida: {source} → {target}.")
