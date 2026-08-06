from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from nexora.intelligence.core import (
	AdapterInvocationError,
	IntelligenceError,
	ProviderAuthenticationError,
	ProviderModelNotFoundError,
	ProviderQuotaExhaustedError,
	ProviderRateLimitError,
	ProviderRecord,
	ProviderTimeoutError,
)

__all__ = [
	"CIRCUIT_STATES",
	"DEFAULT_FAILURE_THRESHOLD",
	"DEFAULT_COOLDOWN_SECONDS",
	"MAX_COOLDOWN_SECONDS",
	"HealthState",
	"record_success",
	"record_failure",
	"begin_trial",
	"is_available",
	"should_retry_same_provider",
	"score_candidate",
	"rank_candidates",
]

CIRCUIT_STATES = frozenset({"Closed", "Open", "Half-Open"})

# Inspirado en el "circuit breaker por proveedor" + "connection cooldown" de
# OmniRoute (analizado en el Bloque 5.2), reimplementado nativo en Python:
# tres fallos seguidos abren el circuito; el enfriamiento crece con cada
# apertura sucesiva (backoff exponencial simple), con un techo para que un
# proveedor nunca quede excluido indefinidamente sin que el Health Monitor
# vuelva a intentarlo.
DEFAULT_FAILURE_THRESHOLD = 3
DEFAULT_COOLDOWN_SECONDS = 60
MAX_COOLDOWN_SECONDS = 900

_COST_HINT_PENALTY = {"Low": 0.0, "Medium": 0.1, "High": 0.2}


@dataclass(frozen=True)
class HealthState:
	"""Estado de salud de un proveedor, persistido en ``NXR AI Provider``
	(campos ``circuit_state``, ``consecutive_failures``, ``degraded_until``).

	Inmutable a propósito: cada función de este módulo recibe un estado y
	devuelve uno nuevo, nunca lo modifica en el sitio — igual que
	``ProviderRecord`` (Bloque 1). Quien la persiste (``orchestrator.py``) es
	responsable de guardar el resultado; este módulo no toca ``frappe`` ni el
	reloj del sistema, así que es probable de forma determinista.
	"""

	circuit_state: str = "Closed"
	consecutive_failures: int = 0
	degraded_until: datetime | None = None

	def __post_init__(self) -> None:
		if self.circuit_state not in CIRCUIT_STATES:
			raise ValueError(f"Estado de circuito inválido: {self.circuit_state!r}.")
		if self.consecutive_failures < 0:
			raise ValueError("consecutive_failures no puede ser negativo.")


def is_available(state: HealthState, *, now: datetime) -> bool:
	"""Un proveedor está disponible para intentarse si su circuito está
	``Closed``, o si estaba ``Open`` pero ya pasó su enfriamiento (pasa a
	comportarse como ``Half-Open``: se le permite un intento de prueba)."""

	if state.circuit_state == "Closed":
		return True
	if state.circuit_state == "Half-Open":
		return True
	# Open: disponible solo si el enfriamiento ya venció.
	return state.degraded_until is not None and now >= state.degraded_until


def record_success(state: HealthState) -> HealthState:
	"""Un intento exitoso siempre cierra el circuito y limpia el historial de
	fallos — sin importar si venía de ``Open``/``Half-Open`` (recuperación) o
	ya estaba ``Closed`` (caso normal)."""

	return HealthState(circuit_state="Closed", consecutive_failures=0, degraded_until=None)


def record_failure(
	state: HealthState,
	*,
	now: datetime,
	retry_after_seconds: int | None = None,
	threshold: int = DEFAULT_FAILURE_THRESHOLD,
) -> HealthState:
	"""Registra un fallo. Un límite de tasa (``retry_after_seconds`` presente)
	abre el circuito de inmediato, sin esperar al umbral — el proveedor ya
	dijo explícitamente que hay que esperar; no tiene sentido intentarlo de
	nuevo antes de eso solo porque no se alcanzó el conteo de fallos.

	En cualquier otro caso, el circuito abre al alcanzar ``threshold`` fallos
	consecutivos. El enfriamiento se calcula como
	``DEFAULT_COOLDOWN_SECONDS * 2 ** (failures - threshold)``, acotado por
	``MAX_COOLDOWN_SECONDS`` — determinista a partir del conteo de fallos, sin
	inferir el enfriamiento anterior desde marcas de tiempo (frágil: ``now``
	puede estar arbitrariamente lejos de cuándo se fijó ``degraded_until`` si
	nadie reintentó justo al vencer). La primera apertura (``failures ==
	threshold``) usa el enfriamiento base sin duplicar; cada fallo adicional
	después de una prueba de recuperación (``Half-Open``) lo duplica.
	"""

	failures = state.consecutive_failures + 1

	if retry_after_seconds is not None:
		cooldown = max(1, retry_after_seconds)
		return HealthState(
			circuit_state="Open",
			consecutive_failures=failures,
			degraded_until=now + timedelta(seconds=cooldown),
		)

	if failures < threshold:
		return HealthState(circuit_state="Closed", consecutive_failures=failures, degraded_until=None)

	cooldown = min(MAX_COOLDOWN_SECONDS, DEFAULT_COOLDOWN_SECONDS * (2 ** (failures - threshold)))
	return HealthState(
		circuit_state="Open",
		consecutive_failures=failures,
		degraded_until=now + timedelta(seconds=cooldown),
	)


def begin_trial(state: HealthState) -> HealthState:
	"""Transición explícita ``Open`` → ``Half-Open`` cuando ya venció el
	enfriamiento y se va a intentar el proveedor de nuevo.

	Quien orquesta (``orchestrator.py``) debe persistir este resultado ANTES
	de intentar la llamada real, no después — así el panel y cualquier otra
	solicitud concurrente ven "en prueba de recuperación" en vez de seguir
	mostrando "Open" mientras el intento está en curso. No es un candado
	distribuido: no impide que dos solicitudes concurrentes elijan el mismo
	proveedor para su prueba de recuperación a la vez, pero si eso ocurre,
	registrar el resultado (``record_success``/``record_failure``) sigue
	siendo correcto para cada una.
	"""

	if state.circuit_state != "Open":
		return state
	return HealthState(
		circuit_state="Half-Open",
		consecutive_failures=state.consecutive_failures,
		degraded_until=state.degraded_until,
	)


# Errores para los que reintentar el MISMO proveedor una vez tiene sentido
# (probablemente transitorios); todos los demás pasan directo al siguiente
# proveedor sin desperdiciar un intento — un reintento no va a arreglar una
# credencial rechazada, un modelo inexistente, una cuota agotada o un
# límite de tasa ya avisado.
_RETRYABLE_SAME_PROVIDER = (ProviderTimeoutError,)
_NEVER_RETRYABLE_SAME_PROVIDER = (
	ProviderAuthenticationError,
	ProviderModelNotFoundError,
	ProviderQuotaExhaustedError,
	ProviderRateLimitError,
)


def should_retry_same_provider(exc: IntelligenceError) -> bool:
	"""``True`` solo para timeouts y errores HTTP genéricos no clasificados
	(posible problema transitorio de red o del lado del proveedor). Nunca
	para autenticación, modelo inexistente o límite de tasa — esos no se
	arreglan reintentando el mismo proveedor de inmediato."""

	if isinstance(exc, _NEVER_RETRYABLE_SAME_PROVIDER):
		return False
	if isinstance(exc, _RETRYABLE_SAME_PROVIDER):
		return True
	# AdapterInvocationError genérico (5xx, fallo de conexión): vale la pena
	# un solo reintento antes de pasar al siguiente proveedor.
	return isinstance(exc, AdapterInvocationError)


def score_candidate(record: ProviderRecord, health: HealthState) -> float:
	"""Menor puntaje = mejor candidato — misma convención que ``priority``
	(Bloque 1). No pretende ser un modelo de 12 factores: combina, de forma
	explicable, la prioridad configurada (factor dominante), una penalización
	pequeña por costo relativo (``cost_hint``, desempate) y una penalización
	por estar en recuperación (``Half-Open``, para preferir un proveedor
	totalmente sano cuando hay uno disponible con la misma prioridad)."""

	score = float(record.priority)
	score += _COST_HINT_PENALTY.get(getattr(record, "cost_hint", None), 0.0)
	if health.circuit_state == "Half-Open":
		score += 5.0
	return score


def rank_candidates(
	records: list[ProviderRecord],
	healths: dict[str, HealthState],
	*,
	now: datetime,
	prefer: str | None = None,
) -> list[ProviderRecord]:
	"""Candidatos disponibles ahora, ordenados de mejor a peor. Si
	``prefer`` señala un proveedor disponible entre los candidatos, va
	primero — mismo contrato que ``router.resolve_provider`` (Bloque 1),
	extendido a una lista completa de intentos en vez de una sola elección.
	"""

	available = [r for r in records if is_available(healths.get(r.provider_key, HealthState()), now=now)]
	ordered = sorted(available, key=lambda r: (score_candidate(r, healths.get(r.provider_key, HealthState())), r.provider_key))
	if prefer is not None:
		preferred = [r for r in ordered if r.provider_key == prefer]
		rest = [r for r in ordered if r.provider_key != prefer]
		ordered = preferred + rest
	return ordered
