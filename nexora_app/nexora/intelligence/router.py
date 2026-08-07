from __future__ import annotations

from nexora.intelligence.core import (
	CAPABILITIES,
	NoProviderAvailableError,
	ProviderConfigError,
	ProviderRecord,
)
from nexora.intelligence.registry import ProviderRegistry


def resolve_provider(
	registry: ProviderRegistry,
	capability: str,
	*,
	prefer: str | None = None,
) -> ProviderRecord:
	"""Elige, de forma determinista, qué proveedor activo atiende una capacidad.

	No ejecuta ninguna llamada externa: solo decide *cuál* proveedor, entre los
	configurados y activos, sería el elegido. Reglas, en orden:

	1. Si ``prefer`` se indica y ese proveedor está activo y soporta la
	   capacidad, se usa sin más criterio.
	2. En otro caso, se ordena por prioridad ascendente (menor número = mayor
	   prioridad) y, ante empate, por ``provider_key``, para que el resultado
	   sea reproducible entre llamadas con la misma configuración.
	3. Si ningún proveedor activo soporta la capacidad, se lanza
	   ``NoProviderAvailableError`` — degradación segura
	   (NEXORA_INTELLIGENCE_ARCHITECTURE.md, sección 3): el módulo llamante
	   debe tratarlo como "la IA no está disponible ahora", nunca como un
	   error fatal del ERP.
	"""

	if capability not in CAPABILITIES:
		raise ProviderConfigError(
			f"Capacidad desconocida: {capability!r}. Use un subconjunto de {sorted(CAPABILITIES)}."
		)

	candidates = registry.list_by_capability(capability)

	if prefer is not None:
		preferred = next((record for record in candidates if record.provider_key == prefer), None)
		if preferred is not None:
			return preferred

	ordered = sorted(candidates, key=lambda record: (record.priority, record.provider_key))
	if not ordered:
		raise NoProviderAvailableError(f"Ningún proveedor de IA activo soporta la capacidad {capability!r}.")
	return ordered[0]
