from __future__ import annotations

from nexora.intelligence.core import (
	AdapterInvocationError,
	AIProviderAdapter,
	ProviderRequest,
	ProviderResponse,
)
from nexora.intelligence.providers.http_support import send_json_request

__all__ = ["CohereLiveAdapter"]


class CohereLiveAdapter(AIProviderAdapter):
	"""Adaptador real para Cohere.

	Única API real de este bloque que soporta ``embedding`` además de
	``text``, cada una contra un endpoint distinto (``/chat`` y ``/embed``).
	No se registra automáticamente (Bloque 2): solo lo instancia
	``nexora.intelligence.runtime`` cuando hay una credencial resuelta.
	"""

	provider_key = "cohere"
	capabilities = ("text", "embedding")
	base_url = "https://api.cohere.com/v1"

	def __init__(
		self,
		*,
		api_key: str,
		default_model: str,
		timeout_seconds: int,
		temperature: float,
		max_tokens: int,
	) -> None:
		self._api_key = api_key
		self._default_model = default_model
		self._timeout_seconds = timeout_seconds
		self._temperature = temperature
		self._max_tokens = max_tokens

	def invoke(self, request: ProviderRequest) -> ProviderResponse:
		if request.capability not in self.capabilities:
			raise AdapterInvocationError(
				f"El adaptador {self.provider_key!r} no soporta la capacidad {request.capability!r}."
			)
		model = str(request.payload.get("model") or self._default_model or "")
		if not model:
			raise AdapterInvocationError(f"No hay modelo configurado para {self.provider_key!r}.")

		headers = {
			"Authorization": f"Bearer {self._api_key}",
			"Content-Type": "application/json",
		}
		if request.capability == "embedding":
			texts = request.payload.get("texts") or [str(request.payload.get("prompt", ""))]
			body: dict = {"model": model, "texts": list(texts)}
			url = f"{self.base_url}/embed"
		else:
			body = {
				"model": model,
				"message": str(request.payload.get("prompt", "")),
				"temperature": request.payload.get("temperature", self._temperature),
				"max_tokens": request.payload.get("max_tokens", self._max_tokens),
			}
			url = f"{self.base_url}/chat"

		data = send_json_request(
			url=url,
			headers=headers,
			payload=body,
			timeout_seconds=self._timeout_seconds,
			provider_key=self.provider_key,
		)
		return ProviderResponse(provider_key=self.provider_key, capability=request.capability, data=data)
