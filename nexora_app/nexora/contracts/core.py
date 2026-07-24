from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable, Mapping

MONEY = Decimal("0.01")

CONTRACT_TRANSITIONS = {
	"Draft": {"In Review", "Cancelled Before Active"},
	"In Review": {"Draft", "Approved", "Cancelled Before Active"},
	"Approved": {"Active", "Cancelled Before Active"},
	"Active": {"Suspended", "Completed", "Early Terminated"},
	"Suspended": {"Active", "Early Terminated"},
	"Completed": {"In Liquidation"},
	"In Liquidation": {"Liquidated"},
	"Liquidated": set(),
	"Early Terminated": set(),
	"Cancelled Before Active": set(),
}
AMENDMENT_TRANSITIONS = {
	"Draft": {"In Review", "Cancelled Before Active"},
	"In Review": {"Draft", "Approved", "Cancelled Before Active"},
	"Approved": {"Active", "Cancelled Before Active"},
	"Active": {"Superseded"},
	"Superseded": set(),
	"Cancelled Before Active": set(),
}
ESTIMATE_TRANSITIONS = {
	"Draft": {"Pending Approval", "Cancelled"},
	"Pending Approval": {"Approved", "Rejected", "Cancelled"},
	"Approved": {"Paid", "Cancelled"},
	"Paid": set(),
	"Rejected": set(),
	"Cancelled": set(),
}
PROFILE_TRANSITIONS = {
	"Draft": {"Active", "Inactive"},
	"Active": {"Suspended", "Expired", "Inactive"},
	"Suspended": {"Active", "Expired", "Inactive"},
	"Expired": {"Active", "Inactive"},
	"Inactive": set(),
}


def money(value: object) -> Decimal:
	try:
		return Decimal(str(value or 0)).quantize(MONEY, rounding=ROUND_HALF_UP)
	except Exception as exc:
		raise ValueError("El importe no es válido.") from exc


def assert_transition(source: str, target: str, transitions: Mapping[str, set[str]]) -> None:
	if source == target:
		return
	if target not in transitions.get(source, set()):
		raise ValueError(f"Transición no permitida: {source} → {target}.")


def validate_period(start: object, end: object) -> None:
	if not start or not end:
		return
	if date.fromisoformat(str(end)) < date.fromisoformat(str(start)):
		raise ValueError("La fecha final no puede ser anterior a la inicial.")


@dataclass(frozen=True)
class ContractAmounts:
	labor: Decimal
	materials: Decimal

	@property
	def total(self) -> Decimal:
		return money(self.labor + self.materials)


def line_amounts(lines: Iterable[Mapping[str, object]]) -> ContractAmounts:
	labor = Decimal("0")
	materials = Decimal("0")
	seen: set[str] = set()
	for index, line in enumerate(lines, start=1):
		key = str(line.get("line_code") or index).strip()
		if key in seen:
			raise ValueError(f"La línea contractual {key} está duplicada.")
		seen.add(key)
		quantity = money(line.get("quantity"))
		rate = money(line.get("unit_rate"))
		if quantity <= 0 or rate < 0:
			raise ValueError("Cada línea requiere cantidad positiva y precio no negativo.")
		amount = money(line.get("amount") or quantity * rate)
		if amount != money(quantity * rate):
			raise ValueError(f"El total de la línea {key} no coincide con cantidad por precio.")
		kind = str(line.get("cost_kind") or "Labor")
		if kind == "Labor":
			labor += amount
		elif kind == "Materials":
			materials += amount
		else:
			raise ValueError("El tipo de costo contractual debe ser Labor o Materials.")
	if not seen:
		raise ValueError("El contrato requiere al menos una línea.")
	return ContractAmounts(money(labor), money(materials))


@dataclass(frozen=True)
class EstimateAmounts:
	gross: Decimal
	advance_amortization: Decimal
	retention: Decimal
	fine: Decimal
	deduction: Decimal
	payable: Decimal


def estimate_amounts(
	gross: object,
	advance_amortization: object = 0,
	retention: object = 0,
	fine: object = 0,
	deduction: object = 0,
) -> EstimateAmounts:
	values = [money(value) for value in (gross, advance_amortization, retention, fine, deduction)]
	gross_value, amortization_value, retention_value, fine_value, deduction_value = values
	if gross_value <= 0:
		raise ValueError("La estimación requiere importe bruto positivo.")
	if any(value < 0 for value in values[1:]):
		raise ValueError("Amortización, retención, multa y deducción no pueden ser negativas.")
	payable = money(gross_value - sum(values[1:], Decimal("0")))
	if payable < 0:
		raise ValueError("Las deducciones no pueden superar el importe bruto.")
	return EstimateAmounts(
		gross_value,
		amortization_value,
		retention_value,
		fine_value,
		deduction_value,
		payable,
	)


def ensure_available(requested: object, available: object, label: str) -> None:
	requested_value = money(requested)
	available_value = money(available)
	if requested_value <= 0:
		raise ValueError(f"El importe {label} debe ser mayor que cero.")
	if requested_value > available_value:
		raise ValueError(
			f"El importe {label} excede el saldo disponible: {requested_value:.2f} > {available_value:.2f}."
		)


def validate_amendment(
	amendment_type: str,
	*,
	labor_delta: object = 0,
	materials_delta: object = 0,
	current_status: str,
	current_end_date: object | None = None,
	new_end_date: object | None = None,
	scope_change: object | None = None,
) -> None:
	labor = money(labor_delta)
	materials = money(materials_delta)
	if amendment_type == "Increase":
		if labor < 0 or materials < 0 or money(labor + materials) <= 0:
			raise ValueError("Una ampliación requiere variaciones no negativas y al menos un incremento.")
	elif amendment_type == "Reduction":
		if labor > 0 or materials > 0 or money(labor + materials) >= 0:
			raise ValueError("Una reducción requiere variaciones no positivas y al menos una disminución.")
	elif amendment_type == "Extension":
		if (
			not new_end_date
			or not current_end_date
			or date.fromisoformat(str(new_end_date)) <= date.fromisoformat(str(current_end_date))
		):
			raise ValueError("Una ampliación de plazo requiere una fecha final posterior a la vigente.")
	elif amendment_type == "Scope Change":
		if not str(scope_change or "").strip():
			raise ValueError("El cambio de alcance requiere el nuevo alcance vigente.")
	elif amendment_type == "Suspension":
		if current_status != "Active":
			raise ValueError("Solo un contrato activo puede suspenderse mediante adenda.")
	elif amendment_type == "Reactivation":
		if current_status != "Suspended":
			raise ValueError("Solo un contrato suspendido puede reactivarse mediante adenda.")
	elif amendment_type == "Early Termination":
		if current_status not in {"Active", "Suspended"}:
			raise ValueError("La terminación anticipada requiere contrato activo o suspendido.")


def amendment_balances(
	labor: object,
	materials: object,
	labor_delta: object,
	materials_delta: object,
	executed_labor: object,
	executed_materials: object,
) -> ContractAmounts:
	result = ContractAmounts(money(labor) + money(labor_delta), money(materials) + money(materials_delta))
	if result.labor < money(executed_labor) or result.materials < money(executed_materials):
		raise ValueError("Una reducción no puede dejar el contrato por debajo de lo ya ejecutado.")
	if result.labor < 0 or result.materials < 0:
		raise ValueError("Una adenda no puede producir saldos contractuales negativos.")
	return ContractAmounts(money(result.labor), money(result.materials))
