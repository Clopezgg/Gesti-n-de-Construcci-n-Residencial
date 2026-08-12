from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any

import frappe

from nexora.financial.context import service_write
from nexora.financial.db import audit
from nexora.intelligence import gateway as _gateway
from nexora.intelligence import runtime as _runtime
from nexora.intelligence.core import (
	AllProvidersExhaustedError,
	IntelligenceError,
	NoProviderAvailableError,
	ProviderRequest,
	ProviderResponse,
)
from nexora.intelligence.orchestrator_core import (
	HealthState,
	begin_trial,
	rank_candidates,
	record_failure,
	record_success,
	should_retry_same_provider,
)
from nexora.intelligence.prompt_optimizer import DEFAULT_MAX_CHARS, optimize_prompt

DOCTYPE = "NXR AI Provider"
USAGE_DOCTYPE = "NXR AI Usage Event"

__all__ = ["execute"]


def _provider_rows() -> list[dict[str, Any]]:
	return frappe.get_all(
		DOCTYPE,
		fields=[
			"name",
			"provider_key",
			"display_name",
			"status",
			"capabilities",
			"priority",
			"cost_hint",
			"circuit_state",
			"consecutive_failures",
			"degraded_until",
		],
	)


def _health_from_row(row: Mapping[str, Any]) -> HealthState:
	return HealthState(
		circuit_state=row.get("circuit_state") or "Closed",
		consecutive_failures=row.get("consecutive_failures") or 0,
		degraded_until=row.get("degraded_until"),
	)


def _persist_health(provider_key: str, health: HealthState, *, error_kind: str | None) -> None:
	with service_write():
		frappe.db.set_value(
			DOCTYPE,
			{"provider_key": provider_key},
			{
				"circuit_state": health.circuit_state,
				"consecutive_failures": health.consecutive_failures,
				"degraded_until": health.degraded_until,
				"last_outcome_at": frappe.utils.now(),
				"last_error_kind": error_kind or "",
			},
		)


def _record_usage(
	*,
	provider_key: str,
	capability: str,
	model: str | None,
	success: bool,
	attempt_number: int,
	error_kind: str | None,
	latency_ms: int,
	response_data: Mapping[str, Any] | None,
	correlation_id: str,
) -> None:
	usage = _extract_usage(response_data) if response_data else {}
	with service_write():
		frappe.get_doc(
			{
				"doctype": USAGE_DOCTYPE,
				"provider_key": provider_key,
				"capability": capability,
				"model": model,
				"success": 1 if success else 0,
				"attempt_number": attempt_number,
				"error_kind": error_kind or "",
				"latency_ms": latency_ms,
				"prompt_tokens": usage.get("prompt_tokens"),
				"completion_tokens": usage.get("completion_tokens"),
				"total_tokens": usage.get("total_tokens"),
				"reported_cost": usage.get("reported_cost"),
				"correlation_id": correlation_id,
			}
		).insert(ignore_permissions=True)


def _extract_usage(data: Mapping[str, Any]) -> dict[str, Any]:
	"""Lee tokens/costo si el proveedor los reportó — nunca los inventa ni
	los calcula con una tabla de precios propia (Bloque 5.2, sección
	"Cost Registry"). Formas ya confirmadas contra proveedores reales en
	este bloque: ``usage.{prompt,completion,total}_tokens`` (OpenAI, Groq,
	Mistral, DeepSeek, OpenRouter), ``usage.cost``/``usage.cost.total_cost``
	(OpenRouter, Perplexity), ``usageMetadata`` (Gemini), ``meta.tokens``
	(Cohere). Un proveedor con una forma distinta simplemente no reporta
	costo/tokens aquí — no se adivina.
	"""

	usage = data.get("usage")
	if isinstance(usage, Mapping):
		cost = usage.get("cost")
		reported_cost = None
		if isinstance(cost, (int, float)):
			reported_cost = cost
		elif isinstance(cost, Mapping):
			reported_cost = cost.get("total_cost")
		return {
			"prompt_tokens": usage.get("prompt_tokens"),
			"completion_tokens": usage.get("completion_tokens"),
			"total_tokens": usage.get("total_tokens"),
			"reported_cost": reported_cost,
		}
	gemini_usage = data.get("usageMetadata")
	if isinstance(gemini_usage, Mapping):
		return {
			"prompt_tokens": gemini_usage.get("promptTokenCount"),
			"completion_tokens": gemini_usage.get("candidatesTokenCount"),
			"total_tokens": gemini_usage.get("totalTokenCount"),
			"reported_cost": None,
		}
	cohere_meta = data.get("meta")
	if isinstance(cohere_meta, Mapping) and isinstance(cohere_meta.get("tokens"), Mapping):
		tokens = cohere_meta["tokens"]
		return {
			"prompt_tokens": tokens.get("input_tokens"),
			"completion_tokens": tokens.get("output_tokens"),
			"total_tokens": None,
			"reported_cost": None,
		}
	return {}


def execute(
	capability: str,
	payload: Mapping[str, Any],
	correlation_id: str,
	*,
	prefer: str | None = None,
	max_prompt_chars: int = DEFAULT_MAX_CHARS,
) -> ProviderResponse:
	"""El Orchestrator central: intenta, en orden, cada proveedor activo y
	capaz hasta obtener una respuesta o agotarlos todos.

	Esta es la "regla de oro" del Bloque 5.2: si un proveedor falla, se
	registra el evento, se degrada si corresponde, y se intenta el siguiente
	mejor proveedor sin detener la solicitud — el usuario nunca ve el fallo
	intermedio, solo el resultado final o, si de verdad no quedó ningún
	proveedor disponible tras intentarlo, un único error claro
	(``AllProvidersExhaustedError``). Si ni siquiera había un candidato con
	quien empezar (nada activo/capaz/sano), se propaga
	``NoProviderAvailableError`` (Bloque 1) sin fingir que se "intentó" algo
	— son situaciones distintas y esta función no las confunde.

	Reutiliza en su totalidad la arquitectura de los Bloques 1-5: el registro
	de proveedores (``gateway.build_registry``), la resolución de credencial y
	configuración (``runtime.build_ready_adapter``), y el contrato
	``AIProviderAdapter``/``ProviderResponse`` del Bloque 1. No duplica
	ninguna de esas piezas — solo añade la decisión de "cuál intentar
	primero, cuándo pasar al siguiente, y cuándo darse por vencido".
	"""

	if isinstance(payload.get("prompt"), str):
		optimized = optimize_prompt(payload["prompt"], max_chars=max_prompt_chars)
		payload = {**payload, "prompt": optimized["text"]}

	rows = _provider_rows()
	names_by_key = {row["provider_key"]: row["name"] for row in rows}
	registry = _gateway.build_registry(rows)
	healths = {row["provider_key"]: _health_from_row(row) for row in rows}
	now = frappe.utils.now_datetime()

	candidates = rank_candidates(registry.list_by_capability(capability), healths, now=now, prefer=prefer)
	if not candidates:
		raise NoProviderAvailableError(
			f"Ningún proveedor de IA activo y sano soporta la capacidad {capability!r}."
		)

	attempts: list[dict[str, str]] = []
	attempt_number = 0
	last_attempted_provider_key = candidates[0].provider_key

	for record in candidates:
		provider_key = record.provider_key
		last_attempted_provider_key = provider_key
		health = healths[provider_key]
		if health.circuit_state == "Open":
			health = begin_trial(health)
			_persist_health(provider_key, health, error_kind=None)

		retries_left = 1  # como máximo, un reintento adicional sobre el MISMO proveedor
		while True:
			attempt_number += 1
			start = time.perf_counter()
			try:
				adapter = _runtime.build_ready_adapter(provider_key, capability=capability)
				request = ProviderRequest(
					capability=capability, payload=payload, correlation_id=correlation_id
				)
				response = adapter.invoke(request)
			except IntelligenceError as exc:
				latency_ms = round((time.perf_counter() - start) * 1000)
				error_kind = type(exc).__name__
				retry_after = getattr(exc, "retry_after_seconds", None)
				health = record_failure(health, now=now, retry_after_seconds=retry_after)
				_persist_health(provider_key, health, error_kind=error_kind)
				_record_usage(
					provider_key=provider_key,
					capability=capability,
					model=None,
					success=False,
					attempt_number=attempt_number,
					error_kind=error_kind,
					latency_ms=latency_ms,
					response_data=None,
					correlation_id=correlation_id,
				)
				attempts.append({"provider_key": provider_key, "error_kind": error_kind})
				audit(
					"ai_orchestrator_attempt_failed",
					DOCTYPE,
					names_by_key[provider_key],
					"",
					correlation_id,
					{
						"provider_key": provider_key,
						"attempt_number": attempt_number,
						"error_kind": error_kind,
					},
				)
				if retries_left > 0 and should_retry_same_provider(exc):
					retries_left -= 1
					continue
				break
			else:
				latency_ms = round((time.perf_counter() - start) * 1000)
				health = record_success(health)
				_persist_health(provider_key, health, error_kind=None)
				_record_usage(
					provider_key=provider_key,
					capability=capability,
					model=response.data.get("model") if isinstance(response.data, Mapping) else None,
					success=True,
					attempt_number=attempt_number,
					error_kind=None,
					latency_ms=latency_ms,
					response_data=response.data if isinstance(response.data, Mapping) else None,
					correlation_id=correlation_id,
				)
				audit(
					"ai_orchestrator_dispatch_succeeded",
					DOCTYPE,
					names_by_key[provider_key],
					"",
					correlation_id,
					{
						"provider_key": provider_key,
						"attempt_number": attempt_number,
						"attempts_before": len(attempts),
					},
				)
				return response

	audit(
		"ai_orchestrator_all_providers_exhausted",
		DOCTYPE,
		names_by_key[last_attempted_provider_key],
		"",
		correlation_id,
		{"capability": capability, "attempts": attempts},
	)
	_notify_administrators_of_exhaustion(capability, attempts, correlation_id)
	raise AllProvidersExhaustedError(
		f"Ningún proveedor de IA disponible pudo atender la capacidad {capability!r} "
		f"tras {len(attempts)} intento(s).",
		attempts=tuple(attempts),
	)


def _notify_administrators_of_exhaustion(
	capability: str, attempts: list[dict[str, str]], correlation_id: str
) -> None:
	"""Notifica a los Administrator de NEXORA cuando el Orchestrator agota
	todos los proveedores — reutiliza el DocType ``NXR Notification``
	(ya existente) directamente, sin pasar por
	``notifications.service.create_notification``: esa función exige la
	acción ``approve`` del usuario que llama, y aquí quien "decide" notificar
	es el propio sistema tras un fallo de infraestructura, no una solicitud
	humana — no hay una regla nueva, solo una escritura de sistema en el
	mismo modelo ya existente.
	"""

	admins = frappe.get_all(
		"Has Role",
		filters={"role": "NEXORA Administrator", "parenttype": "User"},
		pluck="parent",
	)
	summary = ", ".join(f"{a['provider_key']} ({a['error_kind']})" for a in attempts) or "sin intentos"
	with service_write():
		for recipient in set(admins):
			frappe.get_doc(
				{
					"doctype": "NXR Notification",
					"subject": f"IA: ningún proveedor disponible para {capability}",
					"body": f"Todos los proveedores intentados fallaron: {summary}.",
					"notification_type": "Error",
					"channel": "Inbox",
					"priority": "High",
					"recipient_user": recipient,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
