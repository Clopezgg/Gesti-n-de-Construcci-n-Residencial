"""NXR-CNV-0001 / NXR-UX-0009: bootstrap opcional de un proveedor de IA real
para el recorrido de navegador de CI (`nexora-app.yml`, pipeline Docker de
`scripts/nexora_browser_smoke.mjs`).

Este pipeline es distinto del `bench` directo de `nexora-financial.yml`, que
ya prueba `intelligence.orchestrator.execute()` contra un proveedor real en
`test_intelligence_live_integration.py`. Ese `bench` nunca llega al
recorrido de navegador; este módulo cierra esa brecha para el asistente
conversacional (`nexora-assistant`) y la búsqueda que cae en él
(`nexora-search`), reutilizando exactamente el mismo mecanismo de registro
que ya usa esa prueba — nunca una segunda forma de activar un proveedor.

Nunca bloquea un entorno sin la credencial: sin `OPENAI_API_KEY` en el
proceso, esta función no hace nada.
"""

from __future__ import annotations

from nexora.intelligence.credentials import resolve_environment_credential

_PROVIDER_KEY = "openai"


def seed_live_ai_provider_for_ci() -> None:
	if not resolve_environment_credential(_PROVIDER_KEY):
		print("[nexora] OPENAI_API_KEY ausente: se omite el proveedor de IA real para CI.")
		return

	# Importado aquí, no al nivel del módulo: este módulo debe poder importarse
	# en el job liviano `contract` (sin bench/frappe instalado) — mismo motivo
	# por el que register_provider también se importa dentro de la función.
	import frappe

	from nexora.intelligence.service import register_provider

	if not frappe.db.exists("NXR AI Provider", {"provider_key": _PROVIDER_KEY}):
		register_provider(
			{
				"provider_key": _PROVIDER_KEY,
				"display_name": "OpenAI (recorrido real de navegador, CI)",
				"status": "Active",
				"capabilities": "text",
				"idempotency_key": f"ci-browser-ai-provider-{frappe.generate_hash(length=12)}",
			}
		)

	# Mismos valores mínimos y baratos que ya usa test_intelligence_live_integration.py
	# (NXR-AI-0001): modelo económico, pocos tokens, circuito cerrado y limpio.
	frappe.db.set_value(
		"NXR AI Provider",
		{"provider_key": _PROVIDER_KEY},
		{
			"status": "Active",
			"default_model": "gpt-4o-mini",
			"max_tokens": 60,
			"temperature": 0,
			"timeout_seconds": 30,
			"circuit_state": "Closed",
			"consecutive_failures": 0,
			"degraded_until": None,
		},
	)
	# Sin commit manual: `bench execute` confirma la transacción al terminar
	# sin error (mismo criterio que ya sigue nexora_app/nexora en su totalidad
	# — ningún módulo de NEXORA llama frappe.db.commit(), solo el legado
	# erpnext/ lo hace).
	print("[nexora] Proveedor de IA real (openai) activado para el recorrido de navegador de CI.")
