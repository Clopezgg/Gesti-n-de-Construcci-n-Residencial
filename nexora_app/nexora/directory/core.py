from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime

ENTITY_STATES = frozenset({"Draft", "Active", "Blocked", "Inactive", "Consolidated"})
ENTITY_TRANSITIONS = {
	"Draft": frozenset({"Active"}),
	"Active": frozenset({"Blocked", "Inactive", "Consolidated"}),
	"Blocked": frozenset({"Active", "Inactive", "Consolidated"}),
	"Inactive": frozenset(),
	"Consolidated": frozenset(),
}
ROLE_STATES = frozenset({"Proposed", "Active", "Suspended", "Expired", "Revoked"})
ROLE_TRANSITIONS = {
	"Proposed": frozenset({"Active", "Revoked"}),
	"Active": frozenset({"Suspended", "Expired", "Revoked"}),
	"Suspended": frozenset({"Active", "Expired", "Revoked"}),
	"Expired": frozenset(),
	"Revoked": frozenset(),
}
COMPLIANCE_STATES = frozenset({"Pending", "Current", "Expiring", "Expired", "Approved Exception"})
COMPLIANCE_TRANSITIONS = {
	"Pending": frozenset({"Current", "Approved Exception"}),
	"Current": frozenset({"Expiring", "Expired"}),
	"Expiring": frozenset({"Current", "Expired"}),
	"Expired": frozenset({"Current", "Approved Exception"}),
	"Approved Exception": frozenset({"Current", "Expired"}),
}
SENSITIVE_ROLE_TYPES = frozenset({"Administrator", "Owner", "Employee"})


@dataclass(frozen=True)
class DuplicateSignal:
	candidate: str
	score: int
	reasons: tuple[str, ...]


def _ascii(value: object) -> str:
	text = unicodedata.normalize("NFKD", str(value or ""))
	return "".join(character for character in text if not unicodedata.combining(character))


def normalize_name(value: object) -> str:
	text = re.sub(r"[^A-Za-z0-9]+", " ", _ascii(value).upper()).strip()
	text = re.sub(r"\s+", " ", text)
	previous = None
	while text != previous:
		previous = text
		text = re.sub(r"\b([A-Z])\s+(?=[A-Z]\b)", r"\1", text)
	return text


def normalize_identifier(identifier_type: object, value: object) -> str:
	kind = normalize_name(identifier_type).replace(" ", "_")
	text = str(value or "").strip()
	if not kind or not text:
		raise ValueError("El identificador requiere tipo y valor.")
	if kind in {"EMAIL", "CORREO"}:
		normalized = text.casefold()
	elif kind in {"PASSPORT", "PASAPORTE", "RTN", "DNI", "NATIONAL_ID", "TAX_ID"}:
		normalized = re.sub(r"[^A-Za-z0-9]", "", _ascii(text)).upper()
	else:
		normalized = normalize_name(text).replace(" ", "")
	if len(normalized) < 3:
		raise ValueError("El identificador normalizado es demasiado corto.")
	return normalized


def normalize_contact(contact_type: object, value: object) -> str:
	kind = normalize_name(contact_type).replace(" ", "_")
	text = str(value or "").strip()
	if not kind or not text:
		raise ValueError("El contacto requiere tipo y valor.")
	if kind in {"EMAIL", "CORREO"}:
		if "@" not in text or text.startswith("@") or text.endswith("@"):
			raise ValueError("El correo electrónico no es válido.")
		return text.casefold()
	if kind in {"PHONE", "MOBILE", "WHATSAPP", "TELEFONO", "CELULAR"}:
		digits = re.sub(r"\D", "", text)
		if len(digits) < 7 or len(digits) > 15:
			raise ValueError("El número de contacto debe contener entre 7 y 15 dígitos.")
		return f"+{digits}" if text.lstrip().startswith("+") else digits
	return normalize_name(text)


def fingerprint(namespace: str, kind: object, normalized_value: object) -> str:
	payload = f"{namespace.strip().lower()}|{normalize_name(kind)}|{str(normalized_value).strip()}"
	return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def mask_value(value: object, *, visible_tail: int = 4) -> str:
	text = str(value or "")
	if not text:
		return ""
	if "@" in text:
		local, domain = text.split("@", 1)
		visible = local[:1] if local else ""
		return f"{visible}{'*' * max(len(local) - 1, 3)}@{domain}"
	if len(text) <= visible_tail:
		return "*" * len(text)
	return f"{'*' * (len(text) - visible_tail)}{text[-visible_tail:]}"


def assert_transition(previous: str, current: str, transitions: Mapping[str, frozenset[str]]) -> None:
	if previous == current:
		return
	if previous not in transitions or current not in transitions:
		raise ValueError("Estado de directorio desconocido.")
	if current not in transitions[previous]:
		raise ValueError(f"Transición no permitida: {previous} → {current}.")


def _as_date(value: object | None) -> date | None:
	if value in (None, ""):
		return None
	if isinstance(value, datetime):
		return value.date()
	if isinstance(value, date):
		return value
	return date.fromisoformat(str(value))


def validate_period(valid_from: object | None, valid_until: object | None) -> tuple[date | None, date | None]:
	start = _as_date(valid_from)
	end = _as_date(valid_until)
	if start and end and end < start:
		raise ValueError("La fecha final no puede ser anterior a la fecha inicial.")
	return start, end


def periods_overlap(
	left_from: object | None,
	left_until: object | None,
	right_from: object | None,
	right_until: object | None,
) -> bool:
	left_start, left_end = validate_period(left_from, left_until)
	right_start, right_end = validate_period(right_from, right_until)
	minimum = date.min
	maximum = date.max
	return max(left_start or minimum, right_start or minimum) <= min(
		left_end or maximum, right_end or maximum
	)


def duplicate_score(
	*,
	name_matches: bool,
	identifier_matches: int = 0,
	contact_matches: int = 0,
	linked_user_matches: bool = False,
) -> tuple[int, tuple[str, ...]]:
	score = 0
	reasons: list[str] = []
	if identifier_matches:
		score += 100 + max(identifier_matches - 1, 0) * 10
		reasons.append("identificador exacto")
	if linked_user_matches:
		score += 100
		reasons.append("usuario vinculado exacto")
	if contact_matches:
		score += min(contact_matches, 3) * 35
		reasons.append("contacto coincidente")
	if name_matches:
		score += 20
		reasons.append("nombre normalizado coincidente")
	return score, tuple(reasons)


def assert_no_consolidation_cycle(source: str, target: str, merged_into: Mapping[str, str | None]) -> None:
	if not source or not target or source == target:
		raise ValueError("La consolidación requiere entidades de origen y destino diferentes.")
	seen = {source}
	current: str | None = target
	for _ in range(100):
		if not current:
			return
		if current in seen:
			raise ValueError("La consolidación produciría un ciclo de entidades.")
		seen.add(current)
		current = merged_into.get(current)
	raise ValueError("La cadena de consolidación excede el límite seguro.")


def unique_nonempty(values: Iterable[object]) -> bool:
	items = [str(value).strip() for value in values if str(value or "").strip()]
	return len(items) == len(set(items))
