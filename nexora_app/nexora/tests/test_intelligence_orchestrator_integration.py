"""GP-13: pruebas negativas reales del Orchestrator (`intelligence.orchestrator.execute`)
y de `intelligence.service.test_provider_connection`, contra Frappe/MariaDB real.

`test_intelligence_http_support.py` ya prueba, de forma pura, que la capa de
transporte (`http_support.send_json_request`) clasifica correctamente un 401/403
(`ProviderAuthenticationError`) y un timeout (`ProviderTimeoutError`) sin fabricar
ningún éxito. `test_intelligence_orchestrator_core.py` ya prueba, también de forma
pura, que `should_retry_same_provider()` decide bien cuáles de esos errores
justifican un reintento. Ninguna de las dos prueba que esas dos piezas, ya
conectadas dentro de `orchestrator.execute()` (el bucle de reintento real, con
`NXR AI Provider`/`NXR AI Usage Event` reales) o de `service.test_provider_connection`
(la prueba de conexión que expone la administración), se comporten como el
contrato promete: un error transitorio se reintenta una vez sobre el MISMO
proveedor; uno no transitorio (autenticación) nunca se reintenta; y ninguno de
los dos casos jamás termina reportando éxito. Ese es exactamente el hueco que
GP-13 deja abierto para el dominio de proveedores de IA ("credencial inválida,
timeout, 4xx no reintentable") — el equivalente exacto de lo que
`test_sap_integration_integration.py`/`test_whatsapp_channel_integration.py` ya
demuestran para sus propios dominios.

`_runtime.build_ready_adapter` se sustituye por un adaptador de guion
(`_ScriptedAdapter`) en vez de mockear `orchestrator.execute` en sí — mockear
`execute()` (como hace `test_conversation_integration.py`, deliberadamente,
porque ese archivo prueba otra capa) habría probado la superficie equivocada:
el propio bucle de reintento es lo que este archivo necesita ejercitar.
"""

from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.intelligence import service
from nexora.intelligence.core import (
	AllProvidersExhaustedError,
	ProviderAuthenticationError,
	ProviderResponse,
	ProviderTimeoutError,
)


def _key(prefix: str) -> str:
	return f"{prefix}-{uuid.uuid4().hex[:12]}"


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


class _ScriptedAdapter:
	"""Adaptador falso: cada llamada a ``invoke`` consume el siguiente efecto
	programado — una excepción a lanzar o una ``ProviderResponse`` a
	devolver. Cuenta sus llamadas para poder afirmar sobre reintentos reales,
	no solo sobre el resultado final."""

	def __init__(self, effects: list[Exception | ProviderResponse]) -> None:
		self._effects = list(effects)
		self.calls = 0

	def invoke(self, request) -> ProviderResponse:
		self.calls += 1
		effect = self._effects.pop(0)
		if isinstance(effect, Exception):
			raise effect
		return effect


def _register_active_text_provider(owner_email: str, provider_key: str) -> None:
	frappe.set_user(owner_email)
	service.register_provider(
		{
			"provider_key": provider_key,
			"display_name": f"Proveedor de prueba {provider_key}",
			"status": "Active",
			"capabilities": "text",
		}
	)


class TestOrchestratorRetryLoopMariaDB(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		marker = uuid.uuid4().hex[:8]
		cls.manager = _ensure_user(f"nxr-ai-orch-manager-{marker}@example.test", "NEXORA Finance Manager")

	def setUp(self) -> None:
		frappe.set_user(self.manager)

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def test_execute_retries_a_timeout_once_on_the_same_provider_then_succeeds(self) -> None:
		"""``ProviderTimeoutError`` está en ``_RETRYABLE_SAME_PROVIDER``: un
		único reintento sobre el MISMO proveedor antes de rendirse — nunca un
		éxito fabricado en el primer intento fallido."""
		provider_key = _key("nxr-orch-timeout")
		_register_active_text_provider(self.manager, provider_key)
		correlation_id = _key("orch-timeout-correlation")

		success = ProviderResponse(provider_key=provider_key, capability="text", data={"text": "ok"})
		adapter = _ScriptedAdapter([ProviderTimeoutError("Se agotó el tiempo de espera."), success])

		from nexora.intelligence import orchestrator

		with self._patched_adapter(orchestrator, adapter):
			response = orchestrator.execute("text", {"prompt": "hola"}, correlation_id)

		self.assertIs(response, success)
		self.assertEqual(
			2, adapter.calls, "Un timeout debe reintentarse exactamente una vez, no más ni menos."
		)

		usage_events = frappe.get_all(
			"NXR AI Usage Event",
			filters={"correlation_id": correlation_id},
			fields=["success", "error_kind", "attempt_number"],
			order_by="attempt_number asc",
		)
		self.assertEqual(2, len(usage_events))
		self.assertEqual(0, usage_events[0]["success"])
		self.assertEqual("ProviderTimeoutError", usage_events[0]["error_kind"])
		self.assertEqual(1, usage_events[1]["success"])

	def test_execute_never_retries_a_non_retryable_authentication_error(self) -> None:
		"""``ProviderAuthenticationError`` está en
		``_NEVER_RETRYABLE_SAME_PROVIDER``: reintentar la misma credencial
		rechazada no la vuelve válida. Con un único candidato activo, el
		Orchestrator debe agotarlo tras UN solo intento — no dos — y
		terminar en ``AllProvidersExhaustedError``, nunca en un éxito."""
		provider_key = _key("nxr-orch-authfail")
		_register_active_text_provider(self.manager, provider_key)
		correlation_id = _key("orch-authfail-correlation")

		adapter = _ScriptedAdapter(
			[
				ProviderAuthenticationError("El proveedor rechazó la credencial (HTTP 401)."),
				ProviderAuthenticationError(
					"No debería llegar una segunda llamada — este efecto solo existe para "
					"que un reintento indebido produzca un fallo de prueba explícito, no un "
					"IndexError opaco."
				),
			]
		)

		from nexora.intelligence import orchestrator

		with self._patched_adapter(orchestrator, adapter), self.assertRaises(AllProvidersExhaustedError):
			orchestrator.execute("text", {"prompt": "hola"}, correlation_id)

		self.assertEqual(
			1,
			adapter.calls,
			"Un error de autenticación nunca debe reintentarse sobre el mismo proveedor.",
		)

		usage_events = frappe.get_all(
			"NXR AI Usage Event",
			filters={"correlation_id": correlation_id},
			fields=["success", "error_kind"],
		)
		self.assertEqual(1, len(usage_events))
		self.assertEqual(0, usage_events[0]["success"])
		self.assertEqual("ProviderAuthenticationError", usage_events[0]["error_kind"])

	@staticmethod
	def _patched_adapter(orchestrator_module, adapter: _ScriptedAdapter):
		from unittest.mock import patch

		return patch.object(orchestrator_module._runtime, "build_ready_adapter", return_value=adapter)


class TestProviderConnectionReportsRealFailureMariaDB(FrappeTestCase):
	"""``service.test_provider_connection`` es la prueba de conexión real que
	expone la administración (mismo rol de "conexión real" que
	`sap.test_sap_connection`/`whatsapp` ya tienen probado con su propia
	credencial rechazada). Nunca la había ejercitado ninguna prueba con un
	fallo real del adaptador — solo con una clave de proveedor inexistente
	(`test_intelligence_permission_integration.py`), que es un error
	distinto (`ProviderNotFoundError`, antes de tocar ningún adaptador)."""

	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		marker = uuid.uuid4().hex[:8]
		cls.manager = _ensure_user(f"nxr-ai-conn-manager-{marker}@example.test", "NEXORA Finance Manager")

	def setUp(self) -> None:
		frappe.set_user(self.manager)

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def test_a_rejected_credential_is_reported_as_a_real_failure_not_a_fabricated_success(self) -> None:
		provider_key = _key("nxr-conn-authfail")
		_register_active_text_provider(self.manager, provider_key)
		adapter = _ScriptedAdapter(
			[ProviderAuthenticationError("El proveedor rechazó la credencial (HTTP 401).")]
		)

		from unittest.mock import patch

		from nexora.intelligence import service as service_module

		with patch.object(service_module._runtime, "build_ready_adapter", return_value=adapter):
			result = service_module.test_provider_connection({"provider_key": provider_key})

		self.assertFalse(result["success"])
		self.assertIn("credencial", result["reason"].lower())
		self.assertEqual(1, adapter.calls)

	def test_a_timeout_is_reported_as_a_real_failure_not_a_fabricated_success(self) -> None:
		provider_key = _key("nxr-conn-timeout")
		_register_active_text_provider(self.manager, provider_key)
		adapter = _ScriptedAdapter([ProviderTimeoutError("Se agotó el tiempo de espera.")])

		from unittest.mock import patch

		from nexora.intelligence import service as service_module

		with patch.object(service_module._runtime, "build_ready_adapter", return_value=adapter):
			result = service_module.test_provider_connection({"provider_key": provider_key})

		self.assertFalse(result["success"])
		self.assertEqual(1, adapter.calls)
