from __future__ import annotations

from typing import Final

QUALITY_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
	"Open": frozenset({"Passed", "Failed"}),
	"Failed": frozenset({"Corrected"}),
	"Corrected": frozenset({"Passed", "Failed"}),
	"Passed": frozenset({"Closed"}),
	"Closed": frozenset(),
}

RESULT_VALUES: Final[frozenset[str]] = frozenset({"Pass", "Fail", "Not Tested"})


class QualityValidationError(ValueError): ...


class InvalidTransition(QualityValidationError): ...


def assert_transition(current: str, target: str) -> None:
	allowed = QUALITY_TRANSITIONS.get(current)
	if allowed is None or target not in allowed:
		raise InvalidTransition(f"No se permite transición de {current} a {target}")


def assert_valid_result(value: object) -> str:
	text = str(value or "").strip()
	if text and text not in RESULT_VALUES:
		raise QualityValidationError(f"Resultado inválido: {value!r}")
	return text
