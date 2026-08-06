from __future__ import annotations

from nexora.intelligence.providers.openai_compatible_live import OpenAICompatibleLiveAdapter

__all__ = ["GroqLiveAdapter"]


class GroqLiveAdapter(OpenAICompatibleLiveAdapter):
	"""Adaptador real para Groq. No se registra automáticamente (Bloque 2):
	solo lo instancia ``nexora.intelligence.runtime`` cuando hay una
	credencial resuelta."""

	provider_key = "groq"
	capabilities = ("text",)
	base_url = "https://api.groq.com/openai/v1"
