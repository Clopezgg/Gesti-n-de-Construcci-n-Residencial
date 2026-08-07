from __future__ import annotations

from nexora.intelligence.adapters import register_adapter
from nexora.intelligence.core import AIProviderAdapter, ProviderRequest, ProviderResponse
from nexora.intelligence.providers.stub_support import simulated_invoke


@register_adapter
class GeminiStubAdapter(AIProviderAdapter):
	"""Adaptador simulado para Google Gemini.

	No importa ningún SDK de Google ni ningún cliente HTTP: mismo alcance y
	mismas garantías que ``OpenAIStubAdapter`` — ver ese módulo para el
	razonamiento completo. Declara ``audio`` además de ``text``/``vision``
	únicamente para que las pruebas de enrutamiento tengan más de un
	proveedor entre el que elegir por capacidad; no es una afirmación sobre
	un proveedor real, todavía no conectado.
	"""

	provider_key = "gemini"
	capabilities = ("text", "vision", "audio")

	def invoke(self, request: ProviderRequest) -> ProviderResponse:
		return simulated_invoke(self.provider_key, self.capabilities, request)
