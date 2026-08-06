from __future__ import annotations

from nexora.intelligence.providers.openai_compatible_live import OpenAICompatibleLiveAdapter

__all__ = ["DeepSeekLiveAdapter"]


class DeepSeekLiveAdapter(OpenAICompatibleLiveAdapter):
	"""Adaptador real para DeepSeek. No se registra automáticamente (Bloque
	2): solo lo instancia ``nexora.intelligence.runtime`` cuando hay una
	credencial resuelta."""

	provider_key = "deepseek"
	capabilities = ("text",)
	base_url = "https://api.deepseek.com/v1"
