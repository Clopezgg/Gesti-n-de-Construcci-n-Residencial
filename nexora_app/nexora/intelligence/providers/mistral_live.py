from __future__ import annotations

from nexora.intelligence.providers.openai_compatible_live import OpenAICompatibleLiveAdapter

__all__ = ["MistralLiveAdapter"]


class MistralLiveAdapter(OpenAICompatibleLiveAdapter):
	"""Adaptador real para Mistral. No se registra automáticamente (Bloque
	2): solo lo instancia ``nexora.intelligence.runtime`` cuando hay una
	credencial resuelta."""

	provider_key = "mistral"
	capabilities = ("text", "vision")
	base_url = "https://api.mistral.ai/v1"
