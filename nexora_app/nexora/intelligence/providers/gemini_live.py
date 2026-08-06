from __future__ import annotations

from nexora.intelligence.core import (
	AdapterInvocationError,
	AIProviderAdapter,
	ProviderRequest,
	ProviderResponse,
)
from nexora.intelligence.providers.http_support import send_json_request

__all__ = ["GeminiLiveAdapter"]


class GeminiLiveAdapter(AIProviderAdapter):
	"""Adaptador real para Google Gemini.

	API de forma propia (``generateContent``). La credencial va en la
	cabecera ``x-goog-api-key`` — nunca como parámetro de la URL, para que no
	quede en ningún log de proxy o servidor web (Bloque 4, sección 6:
	"nunca exponer credenciales en logs"). No se registra automáticamente
	(Bloque 2): solo lo instancia ``nexora.intelligence.runtime`` cuando hay
	una credencial resuelta.
	"""

	provider_key = "gemini"
	capabilities = ("text", "vision", "audio")
	base_url = "https://generativelanguage.googleapis.com/v1beta"

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
		contents = request.payload.get("contents") or [
			{"parts": [{"text": str(request.payload.get("prompt", ""))}]}
		]
		body = {
			"contents": list(contents),
			"generationConfig": {
				"temperature": request.payload.get("temperature", self._temperature),
				"maxOutputTokens": request.payload.get("max_tokens", self._max_tokens),
			},
		}
		headers = {
			"x-goog-api-key": self._api_key,
			"Content-Type": "application/json",
		}
		data = send_json_request(
			url=f"{self.base_url}/models/{model}:generateContent",
			headers=headers,
			payload=body,
			timeout_seconds=self._timeout_seconds,
			provider_key=self.provider_key,
		)
		return ProviderResponse(provider_key=self.provider_key, capability=request.capability, data=data)
