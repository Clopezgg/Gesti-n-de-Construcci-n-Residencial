from __future__ import annotations

import io
import json
import urllib.error
from unittest import TestCase, mock

from nexora.intelligence.core import (
	AdapterInvocationError,
	ProviderAuthenticationError,
	ProviderModelNotFoundError,
	ProviderRateLimitError,
	ProviderTimeoutError,
)
from nexora.intelligence.providers.http_support import send_json_request


class _FakeResponse:
	def __init__(self, payload: dict) -> None:
		self._body = json.dumps(payload).encode("utf-8")

	def read(self) -> bytes:
		return self._body

	def __enter__(self) -> "_FakeResponse":
		return self

	def __exit__(self, *exc_info) -> None:
		return None


class TestSendJsonRequest(TestCase):
	def test_never_touches_the_real_network(self) -> None:
		"""Confirma que esta suite prueba el manejo de errores, no la red:
		si ``urlopen`` no está interceptado, cualquier llamada real fallaría
		de inmediato por falta de conectividad en este entorno — la prueba
		positiva de abajo depende de que el mock sí esté activo."""

		with mock.patch("urllib.request.urlopen", side_effect=AssertionError("red real tocada")):
			with self.assertRaises(AssertionError):
				send_json_request(
					url="https://example.invalid/v1/chat/completions",
					headers={},
					payload={},
					timeout_seconds=5,
					provider_key="openai",
				)

	def test_returns_the_decoded_json_body_on_success(self) -> None:
		with mock.patch("urllib.request.urlopen", return_value=_FakeResponse({"ok": True})):
			result = send_json_request(
				url="https://example.invalid/v1/chat/completions",
				headers={"Authorization": "Bearer x"},
				payload={"model": "gpt-4o-mini"},
				timeout_seconds=5,
				provider_key="openai",
			)
		self.assertEqual({"ok": True}, result)

	def test_raises_authentication_error_on_http_401(self) -> None:
		error = urllib.error.HTTPError(
			url="https://example.invalid", code=401, msg="Unauthorized", hdrs=None, fp=io.BytesIO(b'{"error":"bad key"}')
		)
		with mock.patch("urllib.request.urlopen", side_effect=error):
			with self.assertRaises(ProviderAuthenticationError):
				send_json_request(
					url="https://example.invalid",
					headers={},
					payload={},
					timeout_seconds=5,
					provider_key="openai",
				)

	def test_raises_authentication_error_on_http_403(self) -> None:
		error = urllib.error.HTTPError(
			url="https://example.invalid", code=403, msg="Forbidden", hdrs=None, fp=io.BytesIO(b"{}")
		)
		with mock.patch("urllib.request.urlopen", side_effect=error):
			with self.assertRaises(ProviderAuthenticationError):
				send_json_request(
					url="https://example.invalid",
					headers={},
					payload={},
					timeout_seconds=5,
					provider_key="anthropic",
				)

	def test_raises_generic_adapter_error_on_other_http_status(self) -> None:
		error = urllib.error.HTTPError(
			url="https://example.invalid", code=500, msg="Server Error", hdrs=None, fp=io.BytesIO(b"{}")
		)
		with mock.patch("urllib.request.urlopen", side_effect=error):
			with self.assertRaises(AdapterInvocationError):
				send_json_request(
					url="https://example.invalid",
					headers={},
					payload={},
					timeout_seconds=5,
					provider_key="openai",
				)

	def test_500_error_is_not_mistaken_for_an_authentication_error(self) -> None:
		error = urllib.error.HTTPError(
			url="https://example.invalid", code=500, msg="Server Error", hdrs=None, fp=io.BytesIO(b"{}")
		)
		with mock.patch("urllib.request.urlopen", side_effect=error):
			try:
				send_json_request(
					url="https://example.invalid",
					headers={},
					payload={},
					timeout_seconds=5,
					provider_key="openai",
				)
			except ProviderAuthenticationError:
				self.fail("un 500 no debe clasificarse como fallo de autenticación")
			except AdapterInvocationError:
				pass

	def test_raises_timeout_error_on_timeout(self) -> None:
		with mock.patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
			with self.assertRaises(ProviderTimeoutError):
				send_json_request(
					url="https://example.invalid",
					headers={},
					payload={},
					timeout_seconds=5,
					provider_key="groq",
				)

	def test_raises_adapter_error_on_connection_failure(self) -> None:
		with mock.patch(
			"urllib.request.urlopen", side_effect=urllib.error.URLError("nombre no resuelto")
		):
			with self.assertRaises(AdapterInvocationError):
				send_json_request(
					url="https://example.invalid",
					headers={},
					payload={},
					timeout_seconds=5,
					provider_key="mistral",
				)

	def test_error_message_never_echoes_the_authorization_header(self) -> None:
		error = urllib.error.HTTPError(
			url="https://example.invalid", code=401, msg="Unauthorized", hdrs=None, fp=io.BytesIO(b"{}")
		)
		secret_header = {"Authorization": "Bearer sk-should-not-leak-1234567890"}
		with mock.patch("urllib.request.urlopen", side_effect=error):
			try:
				send_json_request(
					url="https://example.invalid",
					headers=secret_header,
					payload={},
					timeout_seconds=5,
					provider_key="openai",
				)
			except ProviderAuthenticationError as exc:
				self.assertNotIn("sk-should-not-leak-1234567890", str(exc))

	def test_raises_rate_limit_error_on_http_429(self) -> None:
		error = urllib.error.HTTPError(
			url="https://example.invalid", code=429, msg="Too Many Requests", hdrs=None, fp=io.BytesIO(b"{}")
		)
		with mock.patch("urllib.request.urlopen", side_effect=error):
			with self.assertRaises(ProviderRateLimitError):
				send_json_request(
					url="https://example.invalid",
					headers={},
					payload={},
					timeout_seconds=5,
					provider_key="openai",
				)

	def test_rate_limit_error_includes_retry_after_when_present(self) -> None:
		headers = mock.Mock()
		headers.get.return_value = "30"
		error = urllib.error.HTTPError(
			url="https://example.invalid", code=429, msg="Too Many Requests", hdrs=headers, fp=io.BytesIO(b"{}")
		)
		with mock.patch("urllib.request.urlopen", side_effect=error):
			try:
				send_json_request(
					url="https://example.invalid",
					headers={},
					payload={},
					timeout_seconds=5,
					provider_key="groq",
				)
			except ProviderRateLimitError as exc:
				self.assertIn("30", str(exc))
			else:
				self.fail("se esperaba ProviderRateLimitError")

	def test_rate_limit_error_is_not_mistaken_for_authentication_error(self) -> None:
		error = urllib.error.HTTPError(
			url="https://example.invalid", code=429, msg="Too Many Requests", hdrs=None, fp=io.BytesIO(b"{}")
		)
		with mock.patch("urllib.request.urlopen", side_effect=error):
			try:
				send_json_request(
					url="https://example.invalid",
					headers={},
					payload={},
					timeout_seconds=5,
					provider_key="openai",
				)
			except ProviderAuthenticationError:
				self.fail("un 429 no debe clasificarse como fallo de autenticación")
			except ProviderRateLimitError:
				pass

	def test_raises_model_not_found_error_on_http_404(self) -> None:
		error = urllib.error.HTTPError(
			url="https://example.invalid",
			code=404,
			msg="Not Found",
			hdrs=None,
			fp=io.BytesIO(b'{"error":"model not found"}'),
		)
		with mock.patch("urllib.request.urlopen", side_effect=error):
			with self.assertRaises(ProviderModelNotFoundError):
				send_json_request(
					url="https://example.invalid/models/does-not-exist:generateContent",
					headers={},
					payload={},
					timeout_seconds=5,
					provider_key="gemini",
				)

	def test_model_not_found_error_is_a_kind_of_adapter_invocation_error(self) -> None:
		"""Un llamante que solo captura ``AdapterInvocationError`` (patrón ya
		usado en el resto del subsistema) sigue atrapando este caso sin
		cambios — ``ProviderModelNotFoundError`` hereda de ella."""

		self.assertTrue(issubclass(ProviderModelNotFoundError, AdapterInvocationError))
		self.assertTrue(issubclass(ProviderRateLimitError, AdapterInvocationError))
