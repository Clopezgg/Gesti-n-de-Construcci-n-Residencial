from __future__ import annotations

import copy
import hashlib
import json
import threading
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation as DecimalInvalidOperation, ROUND_HALF_UP
from typing import Any, Callable, Mapping, MutableMapping, Sequence

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
    def from_values(cls, funds: object, reserved: object = 0) -> "SourceState":
        return cls(money(funds), money(reserved))

    @property
    def available(self) -> Decimal:
        return money(self.funds - self.reserved)


@dataclass(frozen=True)
class Allocation:
    source: str
    amount: Decimal


def normalize_allocations(rows: Sequence[Mapping[str, Any]]) -> tuple[Allocation, ...]:
    allocations: list[Allocation] = []
    seen: set[str] = set()
    for row in rows:
        source = str(row.get("source") or row.get("fund_source") or "").strip()
        amount = money(row.get("amount_hnl", row.get("amount")))
        if not source:
            raise FinancialError("Cada asignación requiere una fuente.")
        if source in seen:
            raise FinancialError(f"La fuente {source} está repetida.")
        if amount <= 0:
            raise FinancialError(f"La asignación de {source} debe ser mayor que cero.")
        seen.add(source)
        allocations.append(Allocation(source, amount))
    return tuple(sorted(allocations, key=lambda item: item.source))


def stable_lock_order(rows: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    return tuple(item.source for item in normalize_allocations(rows))


def preview_operation(payload: Mapping[str, Any], source_states: Mapping[str, SourceState]) -> dict[str, Any]:
    operation_type = str(payload.get("operation_type") or "").strip()
    supported = {
        "Outflow",
        "Commitment Reserve",
        "Commitment Execution",
        "Commitment Release",
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
        if amount != 0:
            raise FinancialError("Una reclasificación financiera debe tener importe cero.")
    else:
        if amount <= 0:
            raise FinancialError("El importe debe ser mayor que cero.")
        allocated = money(sum((row.amount for row in allocations), Decimal("0")))
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

        if operation_type == "Outflow":
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
                raise InsufficientFunds(f"La fuente {allocation.source} no tiene reserva suficiente para liberar.")
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

    cost_delta = Decimal("0")
    if payload.get("affects_cost"):
        if operation_type in {"Outflow", "Commitment Execution"}:
            cost_delta = amount
        elif operation_type == "Real Return":
            cost_delta = -amount
    budget_delta = Decimal("0")
    if payload.get("affects_budget"):
        if operation_type in {"Outflow", "Commitment Reserve", "Commitment Execution"}:
            budget_delta = amount
        elif operation_type in {"Commitment Release", "Real Return"}:
            budget_delta = -amount

    preview = {
        "operation_type": operation_type,
        "amount_hnl": f"{amount:.2f}",
        "sources": rows,
        "cost_effect_hnl": f"{money(cost_delta):.2f}",
        "budget_effect_hnl": f"{money(budget_delta):.2f}",
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
