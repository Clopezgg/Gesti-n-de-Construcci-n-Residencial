from __future__ import annotations

from nexora.intelligence.adapters import register_adapter
from nexora.intelligence.core import AIProviderAdapter, ProviderRequest, ProviderResponse
from nexora.intelligence.providers.stub_support import simulated_invoke


@register_adapter
class OpenAIStubAdapter(AIProviderAdapter):
	"""Adaptador simulado para OpenAI.

	No importa el paquete ``openai`` ni ningún cliente HTTP: el Bloque 2
	valida que el contrato (``AIProviderAdapter``) funciona igual para
	varios proveedores, sin conectar ninguno de verdad. Un bloque futuro
	sustituye ``invoke`` por una llamada real; ni el Gateway, ni el Router,
	ni el Provider Manager cambian cuando eso ocurra.
	"""

	provider_key = "openai"
	capabilities = ("text", "vision")

	def invoke(self, request: ProviderRequest) -> ProviderResponse:
		return simulated_invoke(self.provider_key, self.capabilities, request)
