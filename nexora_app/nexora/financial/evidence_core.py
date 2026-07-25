from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

CASH_EVIDENCE_THRESHOLD_HNL = Decimal("2000.00")
PAYMENT_EVIDENCE_METHODS = frozenset({"Deposit", "Transfer"})
SPECIAL_AUTHORIZATION_CATEGORIES = frozenset({"GIFT", "DONATION", "CONTRIBUTION", "SPECIAL"})
EVIDENCE_STATES = frozenset({"Uploaded", "Validated", "Rejected", "Superseded"})
EVIDENCE_TRANSITIONS = {
	"Uploaded": frozenset({"Validated", "Rejected"}),
	"Validated": frozenset({"Superseded"}),
	"Rejected": frozenset({"Superseded"}),
	"Superseded": frozenset(),
}


@dataclass(frozen=True)
class EvidencePolicy:
	required: bool
	reason: str
	requires_external_authorization: bool = False


def _amount(value: object) -> Decimal:
	try:
		amount = Decimal(str(value or 0))
	except (InvalidOperation, ValueError) as exc:
		raise ValueError("El importe de la política de evidencia es inválido.") from exc
	if amount < 0:
		raise ValueError("El importe de la política de evidencia no puede ser negativo.")
	return amount


def evaluate_evidence_policy(
	payment_method: object,
	amount_hnl: object,
	economic_category: object,
	*,
	profile_requires_evidence: bool = False,
) -> EvidencePolicy:
	method = str(payment_method or "").strip().title()
	category = str(economic_category or "").strip().upper()
	amount = _amount(amount_hnl)
	requires_external_authorization = category in SPECIAL_AUTHORIZATION_CATEGORIES
	if profile_requires_evidence or requires_external_authorization:
		return EvidencePolicy(
			required=True,
			reason="La categoría o el tipo de operación exige evidencia verificable.",
			requires_external_authorization=requires_external_authorization,
		)
	if method in PAYMENT_EVIDENCE_METHODS:
		return EvidencePolicy(True, "Los depósitos y transferencias requieren evidencia.")
	if method == "Cash" and amount > CASH_EVIDENCE_THRESHOLD_HNL:
		return EvidencePolicy(True, "El efectivo superior a L2,000 requiere evidencia.")
	return EvidencePolicy(False, "La evidencia es opcional para esta combinación de medio e importe.")


def assert_evidence_transition(previous: str, current: str) -> None:
	if previous == current:
		return
	if previous not in EVIDENCE_STATES or current not in EVIDENCE_STATES:
		raise ValueError("Estado de evidencia desconocido.")
	if current not in EVIDENCE_TRANSITIONS[previous]:
		raise ValueError(f"Transición de evidencia no permitida: {previous} → {current}.")


def normalize_file_content(content: bytes | bytearray | str) -> bytes:
	if isinstance(content, str):
		return content.encode("utf-8")
	if isinstance(content, bytearray):
		return bytes(content)
	if isinstance(content, bytes):
		return content
	raise ValueError("El contenido de evidencia debe ser binario o texto.")


def sha256_content(content: bytes | bytearray | str) -> str:
	return hashlib.sha256(normalize_file_content(content)).hexdigest()


def is_sha256(value: object) -> bool:
	text = str(value or "")
	return len(text) == 64 and all(character in "0123456789abcdef" for character in text.lower())
