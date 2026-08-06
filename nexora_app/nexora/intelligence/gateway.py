from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from nexora.intelligence.core import ProviderRecord, parse_capabilities
from nexora.intelligence.registry import ProviderRegistry
from nexora.intelligence.router import resolve_provider

__all__ = ["build_registry", "resolve"]


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
	atendería. No invoca ningún proveedor: el Bloque 1 termina en la decisión
	de enrutamiento, no en el despacho real — eso corresponde al Model Router
	del Bloque 2 y a los adaptadores de un bloque posterior
	(NEXORA_INTELLIGENCE_ARCHITECTURE.md, sección 26).
	"""

	registry = build_registry(rows)
	return resolve_provider(registry, capability, prefer=prefer)
