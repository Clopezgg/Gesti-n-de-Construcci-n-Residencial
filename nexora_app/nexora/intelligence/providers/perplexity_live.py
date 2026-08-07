from __future__ import annotations

from nexora.intelligence.providers.openai_compatible_live import OpenAICompatibleLiveAdapter

__all__ = ["PerplexityLiveAdapter"]


class PerplexityLiveAdapter(OpenAICompatibleLiveAdapter):
	"""Adaptador real para Perplexity. No se registra automáticamente
	(Bloque 2): solo lo instancia ``nexora.intelligence.runtime`` cuando hay
	una credencial resuelta."""

	provider_key = "perplexity"
	capabilities = ("text",)
	base_url = "https://api.perplexity.ai"
