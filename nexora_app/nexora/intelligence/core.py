from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

PROVIDER_STATUSES = frozenset({"Active", "Inactive", "Error", "Disabled"})

CAPABILITIES = frozenset({"text", "vision", "audio", "embedding"})

_PROVIDER_KEY_RE = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
_MAX_DISPLAY_NAME_LENGTH = 140


class IntelligenceError(ValueError):
	"""Base para todos los errores del subsistema de inteligencia de NEXORA."""


class ProviderConfigError(IntelligenceError):
	"""La configuración de un proveedor no cumple el contrato mínimo."""


class ProviderNotFoundError(IntelligenceError):
	"""Se pidió un proveedor por su clave y no está registrado."""


class NoProviderAvailableError(IntelligenceError):
	"""Ningún proveedor activo satisface la capacidad solicitada."""


class AdapterInvocationError(IntelligenceError):
	"""Un adaptador no pudo atender la solicitud (p. ej. capacidad no soportada).

	Distinto de ``NoProviderAvailableError``: ese lo lanza el Router cuando
	*ningún* candidato existe; este lo lanza un adaptador concreto ya elegido
	cuando, aun así, no puede resolver la solicitud."""


def validate_provider_key(value: str) -> str:
	if not isinstance(value, str) or not _PROVIDER_KEY_RE.match(value):
		raise ProviderConfigError(
			f"Identificador de proveedor inválido: {value!r}. Debe iniciar con una letra "
			"minúscula y usar solo minúsculas, dígitos, guion o guion bajo (2-64 caracteres)."
		)
	return value


def validate_display_name(value: str) -> str:
	text = (value or "").strip()
	if not text or len(text) > _MAX_DISPLAY_NAME_LENGTH:
		raise ProviderConfigError(
			"El nombre visible del proveedor es obligatorio y no puede superar 140 caracteres."
		)
	return text


def validate_status(value: str) -> str:
	if value not in PROVIDER_STATUSES:
		raise ProviderConfigError(
			f"Estado de proveedor inválido: {value!r}. Use uno de {sorted(PROVIDER_STATUSES)}."
		)
	return value


def validate_priority(value: Any) -> int:
	try:
		priority = int(value)
	except (TypeError, ValueError):
		raise ProviderConfigError(f"La prioridad debe ser un entero: {value!r}") from None
	if priority < 0:
		raise ProviderConfigError("La prioridad no puede ser negativa.")
	return priority


def parse_capabilities(value: str | Iterable[str]) -> tuple[str, ...]:
	if isinstance(value, str):
		items = [item.strip() for item in value.split(",") if item.strip()]
	else:
		items = [str(item).strip() for item in value if str(item).strip()]
	if not items:
		raise ProviderConfigError("Debe declarar al menos una capacidad.")
	unknown = sorted(set(items) - CAPABILITIES)
	if unknown:
		raise ProviderConfigError(
			f"Capacidades desconocidas: {unknown}. Use un subconjunto de {sorted(CAPABILITIES)}."
		)
	# Orden estable y sin duplicados: dos configuraciones equivalentes producen
	# siempre la misma representación, lo que mantiene el enrutamiento
	# determinista y la huella de auditoría reproducible.
	return tuple(sorted(set(items)))


@dataclass(frozen=True)
class ProviderRecord:
	"""Configuración validada e inmutable de un proveedor de IA.

	No contiene ninguna credencial. El almacenamiento y la resolución de claves
	es responsabilidad del API Key Manager
	(NEXORA_INTELLIGENCE_ARCHITECTURE.md, sección 8), fuera de alcance del
	Bloque 1: un ``ProviderRecord`` solo describe *qué* proveedor existe, *qué*
	puede hacer y si está activo — nunca *cómo* autenticarse contra él.
	"""

	provider_key: str
	display_name: str
	status: str
	capabilities: tuple[str, ...]
	priority: int = 100

	def __post_init__(self) -> None:
		object.__setattr__(self, "provider_key", validate_provider_key(self.provider_key))
		object.__setattr__(self, "display_name", validate_display_name(self.display_name))
		object.__setattr__(self, "status", validate_status(self.status))
		object.__setattr__(self, "priority", validate_priority(self.priority))
		object.__setattr__(self, "capabilities", parse_capabilities(self.capabilities))

	@property
	def is_active(self) -> bool:
		return self.status == "Active"

	def supports(self, capability: str) -> bool:
		return capability in self.capabilities


@dataclass(frozen=True)
class ProviderRequest:
	"""Solicitud dirigida a un proveedor concreto una vez resuelto.

	Declarado para fijar la forma del contrato; el Bloque 1 no construye ni
	despacha ninguna instancia real de ``ProviderRequest`` contra un proveedor.
	"""

	capability: str
	payload: Mapping[str, Any]
	correlation_id: str


@dataclass(frozen=True)
class ProviderResponse:
	"""Respuesta homogénea que cualquier adaptador de proveedor debe producir.

	Igual que ``ProviderRequest``, fija el contrato para un bloque futuro.
	"""

	provider_key: str
	capability: str
	data: Mapping[str, Any]


class AIProviderAdapter(ABC):
	"""Contrato único que todo adaptador de proveedor de IA debe implementar.

	Ningún módulo de negocio ni el AI Gateway conocen un proveedor concreto:
	solo interactúan con este contrato (agnosticismo de proveedor,
	NEXORA_INTELLIGENCE_ARCHITECTURE.md, sección 3). El Bloque 1 no incluye
	ningún adaptador que implemente esta clase contra un proveedor real —
	existe únicamente para fijar la forma que todo adaptador futuro deberá
	respetar, y para que Provider Manager, Router y Gateway puedan operar y
	probarse sin conocer detalles de un proveedor específico.
	"""

	provider_key: str
	capabilities: tuple[str, ...]

	@abstractmethod
	def invoke(self, request: ProviderRequest) -> ProviderResponse:
		"""Ejecuta la solicitud contra el proveedor concreto.

		No implementado por ningún adaptador en el Bloque 1: no se consume
		ningún proveedor real todavía.
		"""

		raise NotImplementedError
