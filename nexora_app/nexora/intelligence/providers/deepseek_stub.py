from __future__ import annotations

from nexora.intelligence.adapters import register_adapter
from nexora.intelligence.core import AIProviderAdapter, ProviderRequest, ProviderResponse
from nexora.intelligence.providers.stub_support import simulated_invoke


@register_adapter
class DeepSeekAdapter(AIProviderAdapter):
	"""Adaptador simulado para DeepSeek.

	No importa ningún SDK de DeepSeek ni ningún cliente HTTP: mismo alcance y
	mismas garantías que ``OpenAIStubAdapter`` — ver ese módulo para el
	razonamiento completo.
	"""

	provider_key = "deepseek"
	capabilities = ("text",)

	def invoke(self, request: ProviderRequest) -> ProviderResponse:
		return simulated_invoke(self.provider_key, self.capabilities, request)
