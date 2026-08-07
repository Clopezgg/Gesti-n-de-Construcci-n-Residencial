from __future__ import annotations

import json
import os

import frappe

from nexora.intelligence.credentials import resolve_environment_credential
from nexora.intelligence.service import (
	register_provider,
	run_orchestrated_request,
	test_provider_connection,
	update_provider_config,
)

PROVIDER_KEY = "openai"

__all__ = ["run"]


def run() -> dict:
	"""Corrida única de diagnóstico para la integración OpenAI -> OmniRoute.

	Pensado para ``bench --site <site> execute nexora.tools.validation.omniroute_check.run``:
	confirma inyección de la variable de entorno, registra/configura el
	proveedor si todavía no existe, y ejercita la conexión real y el
	fallback del Orchestrator — todo en una sola llamada, sin credenciales
	en el valor de retorno.
	"""

	# Herramienta de diagnóstico server-only invocada por `bench execute`, nunca
	# expuesta como endpoint web: eleva a Administrator para poder ejercitar
	# los mismos RPC que usa el panel admin (ai_manage_provider,
	# ai_test_connection), igual que los *_concurrency_probe.py de este mismo
	# árbol de tests.
	frappe.set_user("Administrator")  # nosemgrep
	result: dict = {}

	result["env_var_present_in_container"] = bool(os.getenv("OPENAI_API_KEY", "").strip())
	result["backend_reads_credential"] = bool(resolve_environment_credential(PROVIDER_KEY))

	if frappe.db.exists("NXR AI Provider", {"provider_key": PROVIDER_KEY}):
		result["provider_already_existed"] = True
	else:
		register_provider(
			json.dumps(
				{
					"provider_key": PROVIDER_KEY,
					"display_name": "OpenAI (via OmniRoute)",
					"status": "Active",
					"capabilities": "text,vision",
					"priority": 10,
				}
			)
		)
		update_provider_config(
			json.dumps(
				{
					"provider_key": PROVIDER_KEY,
					"default_model": "gpt-4o-mini",
					"timeout_seconds": 30,
					"temperature": 0.2,
					"max_tokens": 1024,
				}
			)
		)
		result["provider_registered_now"] = True

	result["test_connection"] = test_provider_connection(json.dumps({"provider_key": PROVIDER_KEY}))
	result["orchestrator_run"] = run_orchestrated_request(
		json.dumps({"capability": "text", "prompt": "ping"})
	)

	return result
