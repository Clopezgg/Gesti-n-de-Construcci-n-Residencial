from __future__ import annotations

from nexora.intelligence.providers.openai_compatible_live import OpenAICompatibleLiveAdapter

__all__ = ["OpenAILiveAdapter"]


class OpenAILiveAdapter(OpenAICompatibleLiveAdapter):
	"""Adaptador real para OpenAI. No se registra automáticamente (Bloque 2):
	solo lo instancia ``nexora.intelligence.runtime`` cuando hay una
	credencial resuelta.

	``base_url`` apunta a OmniRoute, un gateway OpenAI-compatible, en lugar
	de ``api.openai.com`` directamente. Todas las llamadas con
	``provider_key == "openai"`` se enrutan a través de OmniRoute sin
	cambios adicionales en el Orchestrator ni en el panel admin."""

	provider_key = "openai"
	capabilities = ("text", "vision")
	base_url = "https://oc961rno9luetxjwm4t0pzbq.18.217.171.173.sslip.io/v1"
