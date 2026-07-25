from __future__ import annotations

import copy
import hashlib
import json
import threading
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from decimal import InvalidOperation as DecimalInvalidOperation
from typing import Any

MONEY_QUANTUM = Decimal("0.01")
RATE_QUANTUM = Decimal("0.000000001")


class FinancialError(ValueError):
	"""Base exception for deterministic financial validation failures."""


class AllocationMismatch(FinancialError):
	pass


class InsufficientFunds(FinancialError):
	pass


class IdempotencyConflict(FinancialError):
	pass


class InvalidFinancialOperation(FinancialError):
	pass


def money(value: object) -> Decimal:
	try:
		return Decimal(str(value or 0)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
	except (DecimalInvalidOperation, ValueError, TypeError) as exc:
		raise FinancialError(f"Importe inválido: {value!r}") from exc


def rate(value: object) -> Decimal:
	try:
		return Decimal(str(value or 0)).quantize(RATE_QUANTUM, rounding=ROUND_HALF_UP)
	except (DecimalInvalidOperation, ValueError, TypeError) as exc:
		raise FinancialError(f"Tasa inválida: {value!r}") from exc


def validate_source_payload(payload: Mapping[str, Any]) -> dict[str, str]:
	channel = str(payload.get("channel") or "").strip()
	supported = {"Remittance", "Cash", "Deposit", "Transfer", "Other"}
	if channel not in supported:
		raise FinancialError(f"Canal de fuente inválido: {channel!r}")
	original = money(payload.get("original_amount"))
	exchange = rate(payload.get("exchange_rate", 1))
	if original <= 0 or exchange <= 0:
		raise FinancialError("El importe y la tasa deben ser mayores que cero.")
	institution = str(payload.get("institution") or "").strip()
	account = str(payload.get("account_reference") or "").strip()
	reference = str(payload.get("external_reference") or "").strip()
	if channel == "Cash" and (institution or account):
		raise FinancialError("El efectivo no debe exigir ni almacenar banco o cuenta.")
	if channel in {"Deposit", "Transfer"}:
		missing = [
			label
			for label, value in (("institución", institution), ("cuenta", account), ("referencia", reference))
			if not value
		]
		if missing:
			raise FinancialError(f"{channel} requiere {', '.join(missing)}.")
	return {
		"channel": channel,
		"original_amount": f"{original:.2f}",
		"exchange_rate": format(exchange, "f"),
		"amount_hnl": f"{money(original * exchange):.2f}",
	}


def canonical_payload_hash(payload: Mapping[str, Any]) -> str:
	encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
	return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SourceState:
	funds: Decimal
	reserved: Decimal

	@classmethod
	def from_values(cls, funds: object, reserved: object = 0) -> SourceState:
		return cls(money(funds), money(reserved))

	@property
	def available(self) -> Decimal:
		return money(self.funds - self.reserved)


@dataclass(frozen=True)
class Allocation:
	source: str
	amount: Decimal
	related_source: str = ""


def normalize_allocations(rows: Sequence[Mapping[str, Any]]) -> tuple[Allocation, ...]:
	allocations: list[Allocation] = []
	seen: set[str] = set()
	for row in rows:
		source = str(row.get("source") or row.get("fund_source") or "").strip()
		amount = money(row.get("amount_hnl", row.get("amount")))
		related_source = str(row.get("related_source") or row.get("original_source") or "").strip()
		if not source:
			raise FinancialError("Cada asignación requiere una fuente.")
		if source in seen:
			raise FinancialError(f"La fuente {source} está repetida.")
		if amount <= 0:
			raise FinancialError(f"La asignación de {source} debe ser mayor que cero.")
		seen.add(source)
		allocations.append(Allocation(source, amount, related_source))
	return tuple(sorted(allocations, key=lambda item: item.source))


def stable_lock_order(rows: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
	return tuple(item.source for item in normalize_allocations(rows))


def _derived_analytic_effects(payload: Mapping[str, Any]) -> list[dict[str, Any]] | None:
	if "derived_analytic_effects" not in payload:
		return None
	rows: list[dict[str, Any]] = []
	for source in payload.get("derived_analytic_effects") or []:
		dimension = str(source.get("dimension") or "")
		amount = money(source.get("amount_hnl"))
		project = str(source.get("project") or "")
		if dimension not in {"Cost", "Budget", "Savings", "Investment"}:
			raise FinancialError(f"Dimensión analítica derivada inválida: {dimension!r}.")
		if not amount or not project:
			raise FinancialError("Cada efecto analítico derivado requiere proyecto e importe no cero.")
		rows.append(
			{
				"dimension": dimension,
				"amount_hnl": f"{amount:.2f}",
				"cost_center": str(source.get("cost_center") or ""),
				"project": project,
				"economic_category": str(source.get("economic_category") or ""),
				"effect_type": str(source.get("effect_type") or "Analytic Adjustment"),
				"is_reversal": int(bool(source.get("is_reversal"))),
				"reverses_effect": str(source.get("reverses_effect") or ""),
			}
		)
	return rows


def preview_operation(payload: Mapping[str, Any], source_states: Mapping[str, SourceState]) -> dict[str, Any]:
	operation_type = str(payload.get("operation_type") or "").strip()
	operation_code = str(payload.get("operation_code") or "").strip()
	supported = {
		"Outflow",
		"Commitment Reserve",
		"Commitment Execution",
		"Commitment Release",
		"Internal Transfer",
		"Analytic Adjustment",
		"Real Return",
		"Reclassification",
	}
	if operation_type not in supported:
		raise InvalidFinancialOperation(f"Tipo de operación no soportado: {operation_type!r}")

	amount = money(payload.get("amount_hnl", payload.get("amount")))
	allocations = normalize_allocations(payload.get("allocations") or [])

	if operation_type == "Reclassification":
		if allocations:
			raise FinancialError("Una reclasificación no usa asignaciones ni altera fuentes.")
		if operation_code == "DOCUMENT_SUBSTITUTION":
			if amount != 0:
				raise FinancialError("Una sustitución documental debe tener importe cero.")
		elif amount <= 0:
			raise FinancialError("Una reclasificación financiera debe tener importe positivo.")
	elif operation_type == "Analytic Adjustment":
		if allocations:
			raise FinancialError("Un ajuste analítico no usa fuentes ni altera fondos.")
		if amount <= 0:
			raise FinancialError("El ajuste analítico debe tener importe positivo.")
	else:
		if amount <= 0:
			raise FinancialError("El importe debe ser mayor que cero.")
		allocated = money(sum((row.amount for row in allocations), Decimal(0)))
		if allocated != amount:
			raise AllocationMismatch(
				f"Las asignaciones suman {allocated:.2f} y la operación exige {amount:.2f}."
			)

	rows: list[dict[str, str]] = []
	for allocation in allocations:
		if allocation.source not in source_states:
			raise FinancialError(f"La fuente {allocation.source} no existe o no está disponible.")
		before = source_states[allocation.source]
		funds_after = before.funds
		reserved_after = before.reserved

		if operation_type in {"Outflow", "Internal Transfer"}:
			if before.available < allocation.amount:
				raise InsufficientFunds(f"La fuente {allocation.source} no tiene disponible suficiente.")
			funds_after = money(before.funds - allocation.amount)
		elif operation_type == "Commitment Reserve":
			if before.available < allocation.amount:
				raise InsufficientFunds(f"La fuente {allocation.source} no puede reservar ese importe.")
			reserved_after = money(before.reserved + allocation.amount)
		elif operation_type == "Commitment Execution":
			if before.reserved < allocation.amount or before.funds < allocation.amount:
				raise InsufficientFunds(
					f"La fuente {allocation.source} no tiene reserva y fondos suficientes para ejecutar."
				)
			funds_after = money(before.funds - allocation.amount)
			reserved_after = money(before.reserved - allocation.amount)
		elif operation_type == "Commitment Release":
			if before.reserved < allocation.amount:
				raise InsufficientFunds(
					f"La fuente {allocation.source} no tiene reserva suficiente para liberar."
				)
			reserved_after = money(before.reserved - allocation.amount)
		elif operation_type == "Real Return":
			if not payload.get("evidence"):
				raise FinancialError("Una devolución real requiere evidencia comprobable.")
			funds_after = money(before.funds + allocation.amount)

		if funds_after < 0 or reserved_after < 0 or funds_after - reserved_after < 0:
			raise InsufficientFunds(f"La operación produciría saldo negativo en {allocation.source}.")

		rows.append(
			{
				"source": allocation.source,
				"related_source": allocation.related_source,
				"allocation_role": "Source",
				"project": str(payload.get("project") or ""),
				"amount_hnl": f"{allocation.amount:.2f}",
				"balance_before_hnl": f"{before.funds:.2f}",
				"balance_after_hnl": f"{funds_after:.2f}",
				"reserved_before_hnl": f"{before.reserved:.2f}",
				"reserved_after_hnl": f"{reserved_after:.2f}",
				"available_before_hnl": f"{before.available:.2f}",
				"available_after_hnl": f"{money(funds_after - reserved_after):.2f}",
				"funds_delta_hnl": f"{money(funds_after - before.funds):.2f}",
				"reserved_delta_hnl": f"{money(reserved_after - before.reserved):.2f}",
			}
		)

	if operation_type == "Internal Transfer":
		destination = str(payload.get("destination_source") or "").strip()
		if not destination or destination in {row.source for row in allocations}:
			raise FinancialError("La transferencia requiere una fuente de destino distinta.")
		if destination not in source_states:
			raise FinancialError("La fuente de destino no existe o no está disponible.")
		before = source_states[destination]
		funds_after = money(before.funds + amount)
		rows.append(
			{
				"source": destination,
				"related_source": "",
				"allocation_role": "Destination",
				"project": str(payload.get("target_project") or ""),
				"amount_hnl": f"{amount:.2f}",
				"balance_before_hnl": f"{before.funds:.2f}",
				"balance_after_hnl": f"{funds_after:.2f}",
				"reserved_before_hnl": f"{before.reserved:.2f}",
				"reserved_after_hnl": f"{before.reserved:.2f}",
				"available_before_hnl": f"{before.available:.2f}",
				"available_after_hnl": f"{money(funds_after - before.reserved):.2f}",
				"funds_delta_hnl": f"{amount:.2f}",
				"reserved_delta_hnl": "0.00",
			}
		)

	analytic_effects = _derived_analytic_effects(payload)
	if analytic_effects is None:
		analytic_factors = payload.get("analytic_factors") or {}
		if not analytic_factors:
			analytic_factors = {
				"Cost": (
					1
					if payload.get("affects_cost") and operation_type in {"Outflow", "Commitment Execution"}
					else -1
					if payload.get("affects_cost") and operation_type == "Real Return"
					else 0
				),
				"Budget": (
					1
					if payload.get("affects_budget")
					and operation_type in {"Outflow", "Commitment Reserve", "Commitment Execution"}
					else -1
					if payload.get("affects_budget")
					and operation_type in {"Commitment Release", "Real Return"}
					else 0
				),
			}
		analytic_effects = []
		splits = payload.get("analytic_splits") or []
		if not splits and any(int(value or 0) for value in analytic_factors.values()) and amount > 0:
			splits = [{"cost_center": payload.get("cost_center"), "amount_hnl": amount}]
		for split in splits:
			split_amount = money(split.get("amount_hnl", split.get("amount")))
			for dimension in ("Cost", "Budget", "Savings", "Investment"):
				factor = int(analytic_factors.get(dimension, 0) or 0)
				if factor:
					analytic_effects.append(
						{
							"dimension": dimension,
							"amount_hnl": f"{money(split_amount * factor):.2f}",
							"cost_center": str(split.get("cost_center") or ""),
							"project": str(split.get("project") or payload.get("project") or ""),
							"economic_category": str(payload.get("economic_category") or ""),
							"effect_type": "",
							"is_reversal": 0,
							"reverses_effect": "",
						}
					)

	cost_delta = sum(
		(money(row["amount_hnl"]) for row in analytic_effects if row["dimension"] == "Cost"),
		Decimal(0),
	)
	budget_delta = sum(
		(money(row["amount_hnl"]) for row in analytic_effects if row["dimension"] == "Budget"),
		Decimal(0),
	)
	savings_delta = sum(
		(money(row["amount_hnl"]) for row in analytic_effects if row["dimension"] == "Savings"),
		Decimal(0),
	)
	investment_delta = sum(
		(money(row["amount_hnl"]) for row in analytic_effects if row["dimension"] == "Investment"),
		Decimal(0),
	)

	preview = {
		"operation_code": operation_code,
		"operation_type": operation_type,
		"economic_category": str(payload.get("economic_category") or ""),
		"amount_hnl": f"{amount:.2f}",
		"sources": rows,
		"cost_effect_hnl": f"{money(cost_delta):.2f}",
		"budget_effect_hnl": f"{money(budget_delta):.2f}",
		"savings_effect_hnl": f"{money(savings_delta):.2f}",
		"investment_effect_hnl": f"{money(investment_delta):.2f}",
		"analytic_effects": analytic_effects,
		"reference_amount_hnl": str(payload.get("reference_amount_hnl") or "0.00"),
		"reference_balance_before_hnl": str(payload.get("reference_balance_before_hnl") or "0.00"),
		"reference_balance_after_hnl": str(payload.get("reference_balance_after_hnl") or "0.00"),
		"document_to_generate": "NXR Operation",
	}
	preview["preview_hash"] = canonical_payload_hash(preview)
	return preview


class AtomicLedger:
	"""Deterministic in-memory reference engine used to prove invariants before the DB adapter."""

	def __init__(self) -> None:
		self.sources: MutableMapping[str, SourceState] = {}
		self.operations: list[dict[str, Any]] = []
		self.audit: list[dict[str, Any]] = []
		self.idempotency: dict[str, tuple[str, dict[str, Any]]] = {}
		self._counter = 0
		self._lock = threading.RLock()

	def _number(self) -> str:
		self._counter += 1
		if self._counter > 999_999_999_999:
			raise FinancialError("La secuencia global de 12 dígitos se agotó.")
		return f"{self._counter:012d}"

	def create_source(self, name: str, amount_hnl: object) -> None:
		amount = money(amount_hnl)
		if amount <= 0:
			raise FinancialError("La fuente debe iniciar con importe positivo.")
		if name in self.sources:
			raise FinancialError(f"La fuente {name} ya existe.")
		self.sources[name] = SourceState(amount, Decimal("0.00"))

	def execute(
		self,
		payload: Mapping[str, Any],
		idempotency_key: str,
		*,
		fail_after_allocation: int | None = None,
		before_apply: Callable[[], None] | None = None,
	) -> dict[str, Any]:
		with self._lock:
			fingerprint = canonical_payload_hash(payload)
			existing = self.idempotency.get(idempotency_key)
			if existing:
				if existing[0] != fingerprint:
					raise IdempotencyConflict("La clave de idempotencia ya fue usada con otro payload.")
				return copy.deepcopy(existing[1])

			preview = preview_operation(payload, self.sources)
			document_number = self._number()  # never rolled back: a gap is safer than reuse
			snapshot_sources = copy.deepcopy(self.sources)
			snapshot_operations = copy.deepcopy(self.operations)
			snapshot_audit = copy.deepcopy(self.audit)
			try:
				if before_apply:
					before_apply()
				for index, row in enumerate(preview["sources"], start=1):
					if fail_after_allocation == index:
						raise RuntimeError(f"Fallo inyectado después de asignación {index}")
					source = row["source"]
					self.sources[source] = SourceState.from_values(
						row["balance_after_hnl"], row["reserved_after_hnl"]
					)
				result = {
					"document_number": document_number,
					"operation_type": preview["operation_type"],
					"preview_hash": preview["preview_hash"],
					"sources": copy.deepcopy(preview["sources"]),
				}
				self.operations.append(copy.deepcopy(result))
				self.audit.append(
					{
						"event": "operation_executed",
						"document_number": document_number,
						"payload_hash": fingerprint,
					}
				)
				self.idempotency[idempotency_key] = (fingerprint, copy.deepcopy(result))
				return result
			except Exception:
				self.sources = snapshot_sources
				self.operations = snapshot_operations
				self.audit = snapshot_audit
				self.idempotency.pop(idempotency_key, None)
				raise
