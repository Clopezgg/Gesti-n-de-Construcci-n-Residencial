from __future__ import annotations

import urllib.error
from unittest import TestCase, mock

from nexora.integrations.connectivity import check_endpoint_connectivity


class _FakeResponse:
	def __init__(self, status: int = 200) -> None:
		self.status = status

	def __enter__(self):
		return self

	def __exit__(self, *exc_info) -> None:
		return None


class TestCheckEndpointConnectivity(TestCase):
	# NXR-INT-0007: estas pruebas nunca tocan la red real — si el mock de
	# ``urlopen`` no estuviera activo, la primera prueba lo confirmaría fallando.

	def test_never_touches_the_real_network(self) -> None:
		with (
			mock.patch("urllib.request.urlopen", side_effect=AssertionError("red real tocada")),
			self.assertRaises(AssertionError),
		):
			check_endpoint_connectivity("https://example.invalid/health")

	def test_2xx_response_is_a_successful_test(self) -> None:
		with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(200)):
			result = check_endpoint_connectivity("https://example.invalid/health")
		self.assertTrue(result["reachable"])
		self.assertTrue(result["ok"])
		self.assertEqual(200, result["status_code"])

	def test_3xx_response_is_still_a_successful_test(self) -> None:
		with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(302)):
			result = check_endpoint_connectivity("https://example.invalid/health")
		self.assertTrue(result["ok"])

	def test_http_error_response_is_reachable_but_not_ok(self) -> None:
		error = urllib.error.HTTPError(
			"https://example.invalid/health", 500, "Internal Server Error", {}, None
		)
		with mock.patch("urllib.request.urlopen", side_effect=error):
			result = check_endpoint_connectivity("https://example.invalid/health")
		self.assertTrue(result["reachable"])
		self.assertFalse(result["ok"])
		self.assertEqual(500, result["status_code"])

	def test_404_is_reachable_but_not_ok(self) -> None:
		# Regresión directa de NXR-INT-0007: antes de esta corrección, ninguna
		# respuesta se verificaba — un 404 real habría quedado como "Success".
		error = urllib.error.HTTPError("https://example.invalid/health", 404, "Not Found", {}, None)
		with mock.patch("urllib.request.urlopen", side_effect=error):
			result = check_endpoint_connectivity("https://example.invalid/health")
		self.assertTrue(result["reachable"])
		self.assertFalse(result["ok"])
		self.assertEqual(404, result["status_code"])

	def test_timeout_is_not_reachable(self) -> None:
		with mock.patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
			result = check_endpoint_connectivity("https://example.invalid/health", timeout_seconds=3)
		self.assertFalse(result["reachable"])
		self.assertFalse(result["ok"])
		self.assertIsNone(result["status_code"])

	def test_dns_or_connection_error_is_not_reachable(self) -> None:
		error = urllib.error.URLError("nombre no resuelto")
		with mock.patch("urllib.request.urlopen", side_effect=error):
			result = check_endpoint_connectivity("https://example.invalid/health")
		self.assertFalse(result["reachable"])
		self.assertFalse(result["ok"])
		self.assertIn("no resuelto", result["detail"])

	def test_sends_a_user_agent_header(self) -> None:
		with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(200)) as urlopen:
			check_endpoint_connectivity("https://example.invalid/health")
		sent_request = urlopen.call_args.args[0]
		self.assertEqual("NEXORA-Integrations/1.0", sent_request.get_header("User-agent"))

	def test_uses_get_method(self) -> None:
		with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(200)) as urlopen:
			check_endpoint_connectivity("https://example.invalid/health")
		sent_request = urlopen.call_args.args[0]
		self.assertEqual("GET", sent_request.get_method())
