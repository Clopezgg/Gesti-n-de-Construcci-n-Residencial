from __future__ import annotations

from nexora.intelligence.providers.openai_compatible_live import OpenAICompatibleLiveAdapter

__all__ = ["OpenAILiveAdapter"]


class OpenAILiveAdapter(OpenAICompatibleLiveAdapter):
	"""Adaptador real para OpenAI. No se registra automáticamente (Bloque 2):
	solo lo instancia ``nexora.intelligence.runtime`` cuando hay una
	credencial resuelta."""

	provider_key = "openai"
	capabilities = ("text", "vision")
	base_url = "https://api.openai.com/v1"
