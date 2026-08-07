from __future__ import annotations

from nexora.intelligence.core import (
	AdapterInvocationError,
	AIProviderAdapter,
	ProviderRequest,
	ProviderResponse,
)
from nexora.intelligence.providers.http_support import send_json_request

__all__ = ["AnthropicLiveAdapter"]

_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicLiveAdapter(AIProviderAdapter):
	"""Adaptador real para Anthropic (Claude).

	API de forma propia (Messages API): autenticación por cabecera
	``x-api-key`` + ``anthropic-version``, no ``Authorization: Bearer`` como
	los proveedores compatibles con OpenAI. No se registra automáticamente
	(Bloque 2): solo lo instancia ``nexora.intelligence.runtime`` cuando hay
	una credencial resuelta.
	"""

	provider_key = "anthropic"
	capabilities = ("text", "vision")
	base_url = "https://api.anthropic.com/v1"

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
		messages = request.payload.get("messages") or [
			{"role": "user", "content": str(request.payload.get("prompt", ""))}
		]
		body = {
			"model": model,
			"messages": list(messages),
			"max_tokens": request.payload.get("max_tokens", self._max_tokens),
			"temperature": request.payload.get("temperature", self._temperature),
		}
		headers = {
			"x-api-key": self._api_key,
			"anthropic-version": _ANTHROPIC_VERSION,
			"Content-Type": "application/json",
		}
		data = send_json_request(
			url=f"{self.base_url}/messages",
			headers=headers,
			payload=body,
			timeout_seconds=self._timeout_seconds,
			provider_key=self.provider_key,
		)
		return ProviderResponse(provider_key=self.provider_key, capability=request.capability, data=data)
