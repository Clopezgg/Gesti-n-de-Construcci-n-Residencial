from __future__ import annotations

from nexora.intelligence.core import (
	AdapterInvocationError,
	AIProviderAdapter,
	ProviderRequest,
	ProviderResponse,
)
from nexora.intelligence.providers.http_support import send_json_request

__all__ = ["OpenAICompatibleLiveAdapter"]


class OpenAICompatibleLiveAdapter(AIProviderAdapter):
	"""Base para proveedores con una API de chat compatible con OpenAI.

	Seis de los nueve proveedores oficiales (OpenAI, Groq, DeepSeek, Mistral,
	Perplexity, OpenRouter) exponen el mismo contrato REST
	(``POST {base_url}/chat/completions`` con ``Authorization: Bearer``).
	Compartir esta clase evita implementar seis veces la misma construcción
	de solicitud y el mismo manejo de errores (Capítulo 44). Cada proveedor
	solo fija ``provider_key``, ``capabilities`` y ``base_url``.

	No se importa ningún SDK de proveedor: la solicitud se construye a mano y
	se envía con ``nexora.intelligence.providers.http_support`` (``urllib`` de
	la biblioteca estándar).
	"""

	base_url: str

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

	def _require_capability(self, capability: str) -> None:
		if capability not in self.capabilities:
			raise AdapterInvocationError(
				f"El adaptador {self.provider_key!r} no soporta la capacidad {capability!r}. "
				f"Capacidades declaradas: {list(self.capabilities)}."
			)

	def _resolve_model(self, request: ProviderRequest) -> str:
		model = str(request.payload.get("model") or self._default_model or "")
		if not model:
			raise AdapterInvocationError(f"No hay modelo configurado para {self.provider_key!r}.")
		return model

	def _build_messages(self, request: ProviderRequest) -> list[dict[str, str]]:
		messages = request.payload.get("messages")
		if messages:
			return list(messages)
		prompt = str(request.payload.get("prompt", ""))
		return [{"role": "user", "content": prompt}]

	def invoke(self, request: ProviderRequest) -> ProviderResponse:
		self._require_capability(request.capability)
		model = self._resolve_model(request)
		body = {
			"model": model,
			"messages": self._build_messages(request),
			"temperature": request.payload.get("temperature", self._temperature),
			"max_tokens": request.payload.get("max_tokens", self._max_tokens),
		}
		headers = {
			"Authorization": f"Bearer {self._api_key}",
			"Content-Type": "application/json",
		}
		data = send_json_request(
			url=f"{self.base_url}/chat/completions",
			headers=headers,
			payload=body,
			timeout_seconds=self._timeout_seconds,
			provider_key=self.provider_key,
		)
		return ProviderResponse(provider_key=self.provider_key, capability=request.capability, data=data)
