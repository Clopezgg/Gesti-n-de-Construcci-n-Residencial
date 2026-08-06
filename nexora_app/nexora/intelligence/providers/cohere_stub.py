from __future__ import annotations

from nexora.intelligence.adapters import register_adapter
from nexora.intelligence.core import AIProviderAdapter, ProviderRequest, ProviderResponse
from nexora.intelligence.providers.stub_support import simulated_invoke


@register_adapter
class CohereAdapter(AIProviderAdapter):
	"""Adaptador simulado para Cohere.

	No importa ningún SDK de Cohere ni ningún cliente HTTP: mismo alcance y
	mismas garantías que ``OpenAIStubAdapter`` — ver ese módulo para el
	razonamiento completo. Declara ``embedding`` además de ``text`` para que
	las pruebas de enrutamiento tengan un proveedor de embeddings entre el
	que elegir; no es una afirmación certificada sobre el proveedor real,
	todavía no conectado.
	"""

	provider_key = "cohere"
	capabilities = ("text", "embedding")

	def invoke(self, request: ProviderRequest) -> ProviderResponse:
		return simulated_invoke(self.provider_key, self.capabilities, request)
