from __future__ import annotations

from nexora.intelligence.providers.openai_compatible_live import OpenAICompatibleLiveAdapter

__all__ = ["OpenRouterLiveAdapter"]


class OpenRouterLiveAdapter(OpenAICompatibleLiveAdapter):
	"""Adaptador real para OpenRouter. No se registra automáticamente
	(Bloque 2): solo lo instancia ``nexora.intelligence.runtime`` cuando hay
	una credencial resuelta."""

	provider_key = "openrouter"
	capabilities = ("text", "vision")
	base_url = "https://openrouter.ai/api/v1"
