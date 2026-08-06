from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from nexora.intelligence.adapters import AdapterRegistry, build_default_registry
from nexora.intelligence.core import ProviderRecord, ProviderRequest, ProviderResponse, parse_capabilities
from nexora.intelligence.registry import ProviderRegistry
from nexora.intelligence.router import resolve_provider

__all__ = ["build_registry", "resolve", "dispatch"]


def build_registry(rows: Iterable[Mapping[str, Any]]) -> ProviderRegistry:
	"""Construye un ``ProviderRegistry`` en memoria a partir de filas ya leídas.

	No abre conexión ni consulta ninguna base de datos: ``service.py`` lee
	``NXR AI Provider`` y entrega las filas ya materializadas. Cada fila se
	vuelve a validar aquí a través de ``ProviderRecord`` — no se confía
	ciegamente en datos ya persistidos que pudieran haberse editado fuera del
	flujo de servicio.
	"""

	registry = ProviderRegistry()
	for row in rows:
		record = ProviderRecord(
			provider_key=row["provider_key"],
			display_name=row["display_name"],
			status=row["status"],
			capabilities=parse_capabilities(row["capabilities"]),
			priority=row.get("priority", 100),
		)
		registry.register(record)
	return registry


def resolve(
	rows: Iterable[Mapping[str, Any]],
	capability: str,
	*,
	prefer: str | None = None,
) -> ProviderRecord:
	"""Punto único de resolución del AI Gateway para el Bloque 1.

	Dada la lista de proveedores configurados (tal como se leen de
	``NXR AI Provider``) y una capacidad solicitada, decide qué proveedor la
	atendería. No invoca ningún proveedor — para eso está ``dispatch``, que
	además necesita que exista un adaptador de código (Bloque 2) para el
	proveedor resuelto.
	"""

	registry = build_registry(rows)
	return resolve_provider(registry, capability, prefer=prefer)


def dispatch(
	rows: Iterable[Mapping[str, Any]],
	capability: str,
	payload: Mapping[str, Any],
	correlation_id: str,
	*,
	prefer: str | None = None,
	adapters: AdapterRegistry | None = None,
) -> ProviderResponse:
	"""Resuelve un proveedor configurado y lo invoca a través de su adaptador.

	Compone ``resolve`` (Bloque 1: qué proveedor configurado y activo
	atendería la capacidad) con el registro de adaptadores de código del
	Bloque 2 (qué implementación existe para ese proveedor). Que un proveedor
	esté configurado y activo no garantiza que exista un adaptador todavía —
	si no lo hay, se propaga ``ProviderNotFoundError`` en vez de fallar en
	silencio o inventar una respuesta.

	``dispatch`` en sí mismo no toca la red ni conoce qué proveedores existen:
	quien la tocaría, si acaso, es el adaptador resuelto — y el Gateway no
	necesita saber si ese adaptador es simulado o real para funcionar. Ningún
	nombre de proveedor concreto aparece aquí a propósito: esa distinción
	pertenece a ``intelligence/providers/``, no al Gateway.
	"""

	record = resolve(rows, capability, prefer=prefer)
	registry = adapters if adapters is not None else build_default_registry()
	adapter = registry.get(record.provider_key)
	request = ProviderRequest(capability=capability, payload=payload, correlation_id=correlation_id)
	return adapter.invoke(request)
