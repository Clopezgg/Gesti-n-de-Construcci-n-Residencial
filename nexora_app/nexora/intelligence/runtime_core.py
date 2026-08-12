from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nexora.intelligence.config import DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE, DEFAULT_TIMEOUT_SECONDS
from nexora.intelligence.core import (
	AdapterInvocationError,
	AIProviderAdapter,
	CredentialNotConfiguredError,
	ProviderConfigError,
	ProviderDisabledError,
	ProviderNotFoundError,
	parse_capabilities,
)
from nexora.intelligence.providers.anthropic_live import AnthropicLiveAdapter
from nexora.intelligence.providers.cohere_live import CohereLiveAdapter
from nexora.intelligence.providers.deepseek_live import DeepSeekLiveAdapter
from nexora.intelligence.providers.gemini_live import GeminiLiveAdapter
from nexora.intelligence.providers.groq_live import GroqLiveAdapter
from nexora.intelligence.providers.mistral_live import MistralLiveAdapter
from nexora.intelligence.providers.openai_live import OpenAILiveAdapter
from nexora.intelligence.providers.openrouter_live import OpenRouterLiveAdapter
from nexora.intelligence.providers.perplexity_live import PerplexityLiveAdapter

__all__ = ["REAL_ADAPTER_CLASSES", "check_readiness", "prepare_adapter"]

# Mapeo explícito, no el registro automático del Bloque 2 (``adapters.py``):
# un adaptador en vivo solo debe instanciarse cuando ya se confirmó que hay
# una credencial real disponible, una decisión de tiempo de ejecución que el
# registro estático de clases del Bloque 2 no puede tomar por sí mismo. Los
# adaptadores simulados de los Bloques 2/2.1 siguen registrados exactamente
# igual, sin tocarse — este mapeo es un mecanismo aparte, no un reemplazo.
REAL_ADAPTER_CLASSES: dict[str, type[AIProviderAdapter]] = {
	"openai": OpenAILiveAdapter,
	"anthropic": AnthropicLiveAdapter,
	"gemini": GeminiLiveAdapter,
	"groq": GroqLiveAdapter,
	"deepseek": DeepSeekLiveAdapter,
	"mistral": MistralLiveAdapter,
	"cohere": CohereLiveAdapter,
	"perplexity": PerplexityLiveAdapter,
	"openrouter": OpenRouterLiveAdapter,
}


def check_readiness(
	row: Mapping[str, Any],
	secret: str | None,
	*,
	capability: str | None = None,
) -> dict[str, Any]:
	"""Evalúa si un proveedor está listo para usarse, sin construir nada.

	Pura: no toca ``frappe`` ni la red. Devuelve un reporte en vez de lanzar,
	para que un endpoint de solo lectura ("validar proveedor", "consultar
	disponibilidad") pueda mostrarlo completo sin depender de capturar
	excepciones una por una. ``prepare_adapter`` reutiliza exactamente esta
	misma función y sí lanza, para el camino que necesita construir una
	instancia real o fallar con claridad.
	"""

	reasons: list[str] = []

	status = row.get("status")
	if status != "Active":
		reasons.append(f"El proveedor está {status!r}, no Active.")

	try:
		capabilities = parse_capabilities(row.get("capabilities", ""))
	except Exception:  # noqa: BLE001 -- cualquier dato malformado se reporta, no se propaga
		capabilities = ()
		reasons.append("Las capacidades declaradas no son válidas.")

	if capability and capability not in capabilities:
		reasons.append(f"El proveedor no declara la capacidad {capability!r}.")

	if not row.get("default_model"):
		reasons.append("No hay modelo por defecto configurado.")

	if row.get("provider_key") not in REAL_ADAPTER_CLASSES:
		reasons.append("No existe todavía un adaptador real implementado para este proveedor.")

	has_credential = bool(secret)
	if not has_credential:
		reasons.append("No hay credencial configurada (ni variable de entorno ni base de datos).")

	return {
		"provider_key": row.get("provider_key"),
		"ready": not reasons,
		"has_credential": has_credential,
		"capabilities": list(capabilities),
		"reasons": reasons,
	}


def prepare_adapter(
	row: Mapping[str, Any],
	secret: str | None,
	*,
	capability: str | None = None,
) -> AIProviderAdapter:
	"""Valida y construye un adaptador en vivo, listo para invocarse.

	Lanza la excepción más específica disponible en vez de un reporte
	genérico — a diferencia de ``check_readiness``, este camino es para un
	llamante que va a *usar* el resultado, no a mostrarlo.
	"""

	status = row.get("status")
	if status != "Active":
		raise ProviderDisabledError(f"El proveedor {row.get('provider_key')!r} está {status!r}, no Active.")

	capabilities = parse_capabilities(row.get("capabilities", ""))
	if capability and capability not in capabilities:
		raise AdapterInvocationError(
			f"El proveedor {row.get('provider_key')!r} no declara la capacidad {capability!r}."
		)

	default_model = row.get("default_model")
	if not default_model:
		raise ProviderConfigError(f"El proveedor {row.get('provider_key')!r} no tiene un modelo por defecto.")

	if not secret:
		raise CredentialNotConfiguredError(f"No hay credencial configurada para {row.get('provider_key')!r}.")

	adapter_cls = REAL_ADAPTER_CLASSES.get(row.get("provider_key"))
	if adapter_cls is None:
		raise ProviderNotFoundError(
			f"No existe un adaptador real implementado para {row.get('provider_key')!r}."
		)

	return adapter_cls(
		api_key=secret,
		default_model=default_model,
		timeout_seconds=row.get("timeout_seconds") or DEFAULT_TIMEOUT_SECONDS,
		temperature=row["temperature"] if row.get("temperature") is not None else DEFAULT_TEMPERATURE,
		max_tokens=row.get("max_tokens") or DEFAULT_MAX_TOKENS,
	)
