"""NXR-AI-0001 / NXR-CNV-0001 / NXR-UX-0009: llamada real y viva a un proveedor de IA.

Requiere bench + MariaDB reales, más una credencial real de servidor
(``OPENAI_API_KEY``, resuelta por ``intelligence.credentials.
resolve_environment_credential`` — la misma variable que ya usaría un
despliegue real). Sin esa variable, la clase completa se salta: ninguna otra
prueba de este repositorio hace una llamada de red real a un proveedor de
IA, así que esta es deliberadamente la única.

Ejercita exactamente el camino real que usan tanto el Gateway operacional
(NXR-AI-0001) como el motor conversacional (NXR-CNV-0001,
``conversation.nlu.interpret`` → ``orchestrator.execute``) y, por lo tanto,
la búsqueda en lenguaje natural que depende de él (NXR-UX-0009):
``intelligence.orchestrator.execute("text", ...)`` sin ningún doble de
prueba — mismo mecanismo, mismo registro de uso real
(``NXR AI Usage Event``), mismo circuito real.

Costo real, deliberadamente mínimo: un modelo económico, ``max_tokens``
bajo, una sola llamada.
"""

from __future__ import annotations

import os
import unittest
import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.intelligence.core import ProviderResponse
from nexora.intelligence.orchestrator import execute as orchestrator_execute

_HAS_LIVE_CREDENTIAL = bool(os.getenv("OPENAI_API_KEY", "").strip())


def _key(prefix: str) -> str:
	return f"{prefix}-{uuid.uuid4().hex}"


def _ensure_user(email: str, role: str) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@", 1)[0],
				"enabled": 1,
				"send_welcome_email": 0,
				"roles": [{"role": role}],
			}
		).insert(ignore_permissions=True)
	return email


@unittest.skipUnless(
	_HAS_LIVE_CREDENTIAL,
	"OPENAI_API_KEY no está configurada en este entorno — sin credencial real, esta clase no puede "
	"ejercer NXR-AI-0001/NXR-CNV-0001/NXR-UX-0009 contra un proveedor de IA vivo.",
)
class TestIntelligenceLiveOpenAIMariaDB(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		marker = uuid.uuid4().hex[:8]
		cls.manager = _ensure_user(f"nxr-ai-live-manager-{marker}@example.test", "NEXORA Finance Manager")
		cls.provider_key = "openai"
		if not frappe.db.exists("NXR AI Provider", {"provider_key": cls.provider_key}):
			frappe.set_user(cls.manager)
			from nexora.intelligence.service import register_provider

			register_provider(
				{
					"provider_key": cls.provider_key,
					"display_name": "OpenAI (prueba real NXR-AI-0001)",
					"status": "Active",
					"capabilities": "text",
					"idempotency_key": _key("ai-live-provider"),
				}
			)
		frappe.db.set_value(
			"NXR AI Provider",
			{"provider_key": cls.provider_key},
			{
				"status": "Active",
				"default_model": "gpt-4o-mini",
				"max_tokens": 16,
				"temperature": 0,
				"timeout_seconds": 30,
				"circuit_state": "Closed",
				"consecutive_failures": 0,
				"degraded_until": None,
			},
		)

	def setUp(self) -> None:
		frappe.set_user(self.manager)

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def test_orchestrator_execute_reaches_a_real_provider_and_returns_a_structured_response(self) -> None:
		"""Mismo camino exacto que ``conversation.nlu.interpret`` — sin ningún
		doble de prueba entre este test y la Graph API real de OmniRoute/OpenAI."""
		correlation_id = _key("ai-live-correlation")
		response = orchestrator_execute(
			"text",
			{
				"messages": [
					{
						"role": "user",
						"content": "Responde con una sola palabra: prueba.",
					}
				],
			},
			correlation_id,
		)
		self.assertIsInstance(response, ProviderResponse)
		self.assertEqual("openai", response.provider_key)
		self.assertEqual("text", response.capability)
		self.assertTrue(response.data, "El proveedor real no devolvió ningún contenido.")

		usage_events = frappe.get_all(
			"NXR AI Usage Event",
			filters={"correlation_id": correlation_id},
			fields=["provider_key", "capability", "success", "model"],
		)
		self.assertEqual(1, len(usage_events))
		self.assertEqual(1, usage_events[0]["success"])
		self.assertEqual("openai", usage_events[0]["provider_key"])


if __name__ == "__main__":
	unittest.main()
