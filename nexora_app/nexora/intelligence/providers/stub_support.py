from __future__ import annotations

from nexora.intelligence.core import AdapterInvocationError, ProviderRequest, ProviderResponse


def simulated_invoke(
	provider_key: str,
	capabilities: tuple[str, ...],
	request: ProviderRequest,
) -> ProviderResponse:
	"""Produce una respuesta simulada y determinista, sin tocar la red.

	Compartido por los adaptadores stub del Bloque 2 para no triplicar la
	misma validación y el mismo formato de respuesta (Capítulo 44: toda
	regla en un único lugar). Ningún adaptador real de un bloque futuro debe
	reutilizar esta función: un adaptador real invoca de verdad al
	proveedor y esta función, por diseño, nunca lo hace.
	"""

	if request.capability not in capabilities:
		raise AdapterInvocationError(
			f"El adaptador {provider_key!r} no soporta la capacidad {request.capability!r}. "
			f"Capacidades declaradas: {list(capabilities)}."
		)
	return ProviderResponse(
		provider_key=provider_key,
		capability=request.capability,
		data={
			"simulated": True,
			"provider_key": provider_key,
			"capability": request.capability,
			"correlation_id": request.correlation_id,
			"echo": dict(request.payload),
			"note": "Respuesta simulada del Bloque 2: no se contactó ningún proveedor real.",
		},
	)
