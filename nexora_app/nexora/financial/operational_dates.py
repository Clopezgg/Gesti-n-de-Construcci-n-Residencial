from __future__ import annotations

from datetime import date


class OperationalDateError(ValueError):
	pass


def parse_document_date(value: object, *, fallback: date | None = None) -> date:
	raw = str(value or "").strip()
	if not raw:
		if fallback is None:
			raise OperationalDateError("La fecha del documento es obligatoria.")
		return fallback
	try:
		return date.fromisoformat(raw[:10])
	except ValueError as exc:
		raise OperationalDateError("La fecha del documento no es válida.") from exc


def validate_document_date(
	value: object,
	*,
	today: date,
	reference_date: object | None = None,
	fallback: date | None = None,
) -> date:
	document_date = parse_document_date(value, fallback=fallback)
	if document_date > today:
		raise OperationalDateError("La fecha del documento no puede estar en el futuro.")
	if reference_date:
		original_date = parse_document_date(reference_date)
		if document_date < original_date:
			raise OperationalDateError(
				"La fecha de una anulación, cancelación o corrección no puede ser anterior al documento original."
			)
	return document_date


def month_key(value: date) -> str:
	return value.strftime("%Y-%m")
