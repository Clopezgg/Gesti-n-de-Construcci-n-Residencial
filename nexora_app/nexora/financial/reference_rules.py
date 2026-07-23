from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Mapping, Sequence

from nexora.financial.core import FinancialError, money

ANALYTIC_DIMENSIONS = ("Cost", "Budget", "Savings", "Investment")
SEGREGATED_OPERATION_CODES = frozenset(
	{
		"INTERNAL_TRANSFER",
		"ADVANCE_DISBURSEMENT",
		"ADVANCE_SETTLEMENT",
		"RECLASSIFICATION",
		"REAL_RETURN",
		"REVERSAL_NO_CASH",
		"DOCUMENT_SUBSTITUTION",
	}
)


@dataclass(frozen=True)
class ReferenceBalance:
	original: Decimal
	consumed: Decimal
	available: Decimal
	requested: Decimal
	remaining: Decimal

	def as_payload(self) -> dict[str, str]:
		return {
			"reference_amount_hnl": f"{self.original:.2f}",
			"reference_balance_before_hnl": f"{self.available:.2f}",
			"reference_balance_after_hnl": f"{self.remaining:.2f}",
		}


def validate_segregation(requester: object, approved_by: object, executed_by: object) -> None:
	identities = [str(value or "").strip() for value in (requester, approved_by, executed_by)]
	if any(not value for value in identities) or len(set(identities)) != 3:
		raise FinancialError("Solicitante, aprobador y ejecutor deben ser tres usuarios distintos.")


def validate_advance_dates(operation_date: object, due_date: object) -> None:
	try:
		issued = date.fromisoformat(str(operation_date or ""))
		due = date.fromisoformat(str(due_date or ""))
	except ValueError as exc:
		raise FinancialError("El anticipo requiere fecha y vencimiento válidos.") from exc
	if due < issued:
		raise FinancialError("El vencimiento del anticipo no puede ser anterior a su fecha.")


def bounded_reference_amount(
	original_amount: object,
	consumed_amount: object,
	requested_amount: object | None,
	*,
	label: str,
) -> ReferenceBalance:
	original = money(original_amount)
	consumed = money(consumed_amount)
	if original <= 0:
		raise FinancialError(f"El documento original no tiene importe {label} positivo.")
	if consumed < 0 or consumed > original:
		raise FinancialError(f"El saldo {label} del documento original es inconsistente.")
	available = money(original - consumed)
	requested = available if requested_amount in (None, "", 0, "0", "0.00") else money(requested_amount)
	if requested <= 0:
		raise FinancialError(f"El importe {label} debe ser mayor que cero.")
	if requested > available:
		raise FinancialError(
			f"El importe {label} {requested:.2f} supera el saldo disponible {available:.2f}."
		)
	return ReferenceBalance(
		original=original,
		consumed=consumed,
		available=available,
		requested=requested,
		remaining=money(available - requested),
	)


def available_amount_from_effects(original_amount: object, effects: Sequence[Mapping[str, Any]]) -> Decimal:
	original = money(original_amount)
	if original <= 0:
		raise FinancialError("El documento original no tiene importe positivo.")
	capacities: list[Decimal] = []
	for effect in effects:
		amount = money(effect.get("amount_hnl"))
		remaining = money(effect.get("remaining_hnl", amount))
		if effect.get("dimension") not in ANALYTIC_DIMENSIONS or amount <= 0:
			continue
		if remaining < 0 or remaining > amount:
			raise FinancialError("El saldo de un efecto original es inconsistente.")
		capacities.append(money(original * remaining / amount))
	if not capacities:
		raise FinancialError("El documento original no conserva efectos analíticos disponibles.")
	return min([original, *capacities])


def derive_reference_effects(
	original_amount: object,
	requested_amount: object,
	effects: Sequence[Mapping[str, Any]],
	*,
	mode: str,
	target_category: str | None = None,
	target_cost_center: str | None = None,
) -> list[dict[str, Any]]:
	if mode not in {"reclassification", "reversal"}:
		raise FinancialError(f"Modo de derivación inválido: {mode}.")
	original = money(original_amount)
	requested = money(requested_amount)
	available = available_amount_from_effects(original, effects)
	if requested <= 0 or requested > available:
		raise FinancialError(
			f"El importe solicitado {requested:.2f} supera el saldo analítico disponible {available:.2f}."
		)
	if mode == "reclassification" and not str(target_category or "").strip():
		raise FinancialError("La reclasificación requiere una clasificación nueva.")

	ratio = requested / original
	rows: list[dict[str, Any]] = []
	classification_changed = False
	for effect in effects:
		dimension = str(effect.get("dimension") or "")
		amount = money(effect.get("amount_hnl"))
		remaining = money(effect.get("remaining_hnl", amount))
		if dimension not in ANALYTIC_DIMENSIONS or amount <= 0:
			continue
		delta = money(amount * ratio)
		if delta <= 0:
			continue
		if delta > remaining:
			raise FinancialError(
				f"El efecto {effect.get('name')} solo conserva {remaining:.2f} reversible."
			)
		base = {
			"dimension": dimension,
			"project": str(effect.get("project") or ""),
			"cost_center": str(effect.get("cost_center") or ""),
			"economic_category": str(effect.get("economic_category") or ""),
			"reverses_effect": str(effect.get("name") or ""),
		}
		rows.append(
			{
				**base,
				"amount_hnl": f"{-delta:.2f}",
				"effect_type": "Reclassification" if mode == "reclassification" else "Reversed",
				"is_reversal": 1,
			}
		)
		if mode == "reclassification":
			new_cost_center = str(target_cost_center or effect.get("cost_center") or "")
			classification_changed = classification_changed or (
				str(target_category) != str(effect.get("economic_category") or "")
				or new_cost_center != str(effect.get("cost_center") or "")
			)
			rows.append(
				{
					"dimension": dimension,
					"amount_hnl": f"{delta:.2f}",
					"project": str(effect.get("project") or ""),
					"cost_center": new_cost_center,
					"economic_category": str(target_category),
					"effect_type": "Reclassification",
					"is_reversal": 0,
					"reverses_effect": "",
				}
			)
	if not rows:
		raise FinancialError("No existen efectos analíticos originales para derivar la corrección.")
	if mode == "reclassification" and not classification_changed:
		raise FinancialError("La clasificación nueva debe cambiar categoría o centro de costo.")
	return rows


def validate_return_allocations(
	original_allocations: Mapping[str, object],
	prior_returned: Mapping[str, object],
	requested_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, str]], Decimal, Decimal]:
	if not requested_rows:
		raise FinancialError("La devolución real requiere al menos una fuente de restitución.")
	seen_original: set[str] = set()
	normalized: list[dict[str, str]] = []
	total_requested = Decimal("0")
	total_available = Decimal("0")
	for source, amount in original_allocations.items():
		total_available += money(amount) - money(prior_returned.get(source, 0))
	for row in requested_rows:
		target_source = str(row.get("source") or row.get("fund_source") or "").strip()
		explicit_original = str(row.get("original_source") or row.get("related_source") or "").strip()
		original_source = explicit_original or target_source
		if not target_source:
			raise FinancialError("Cada devolución requiere fuente de restitución.")
		if target_source != original_source and not explicit_original:
			raise FinancialError("Una fuente distinta requiere relación explícita con la fuente original.")
		if original_source not in original_allocations:
			raise FinancialError(f"La fuente {original_source} no participó en la salida original.")
		if original_source in seen_original:
			raise FinancialError(f"La fuente original {original_source} está repetida en la devolución.")
		amount = money(row.get("amount_hnl", row.get("amount")))
		available = money(original_allocations[original_source]) - money(prior_returned.get(original_source, 0))
		if amount <= 0:
			raise FinancialError("Cada importe devuelto debe ser mayor que cero.")
		if amount > available:
			raise FinancialError(
				f"La devolución para {original_source} supera el saldo recuperable {available:.2f}."
			)
		seen_original.add(original_source)
		total_requested += amount
		normalized.append(
			{
				"source": target_source,
				"related_source": original_source,
				"amount_hnl": f"{amount:.2f}",
			}
		)
	return normalized, money(total_requested), money(total_available)
