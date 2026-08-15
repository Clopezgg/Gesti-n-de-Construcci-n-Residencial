"""Pruebas de unidad reales de `nexora.integrations.sap_core` — sin Frappe,
sin red. Ejecuta lógica real con entradas reales, no solo patrones de texto
sobre el código fuente (eso ya lo cubre `test_sap_integration_contract.py`).
"""

from __future__ import annotations

import base64
import unittest

from nexora.integrations.sap_core import (
	NEVER_RETRYABLE_HTTP_STATUS,
	RETRYABLE_HTTP_STATUS,
	basic_auth_header,
	build_url,
	is_retryable_status,
	oauth_cache_ttl_seconds,
)


class TestIsRetryableStatus(unittest.TestCase):
	def test_transient_server_errors_are_retryable(self) -> None:
		for code in (408, 429, 500, 502, 503, 504):
			with self.subTest(code=code):
				self.assertTrue(is_retryable_status(code))

	def test_auth_and_client_errors_are_never_retryable(self) -> None:
		for code in (400, 401, 403, 404, 405, 409, 422):
			with self.subTest(code=code):
				self.assertFalse(is_retryable_status(code))

	def test_success_codes_are_not_in_either_set(self) -> None:
		for code in (200, 201, 204):
			with self.subTest(code=code):
				self.assertNotIn(code, RETRYABLE_HTTP_STATUS)
				self.assertNotIn(code, NEVER_RETRYABLE_HTTP_STATUS)

	def test_the_two_status_sets_never_overlap(self) -> None:
		self.assertEqual(set(), RETRYABLE_HTTP_STATUS & NEVER_RETRYABLE_HTTP_STATUS)


class TestBasicAuthHeader(unittest.TestCase):
	def test_encodes_username_and_password_as_standard_base64_basic_auth(self) -> None:
		header = basic_auth_header("nexora_user", "s3cr3t")
		self.assertTrue(header.startswith("Basic "))
		decoded = base64.b64decode(header.removeprefix("Basic ")).decode("utf-8")
		self.assertEqual("nexora_user:s3cr3t", decoded)

	def test_never_leaks_the_raw_password_in_the_header_string(self) -> None:
		header = basic_auth_header("user", "hunter2")
		self.assertNotIn("hunter2", header)


class TestBuildUrl(unittest.TestCase):
	def test_joins_base_and_path_with_exactly_one_slash(self) -> None:
		self.assertEqual(
			"https://sap.example.com/api/orders",
			build_url("https://sap.example.com", "api/orders"),
		)

	def test_tolerates_trailing_and_leading_slashes_on_both_sides(self) -> None:
		self.assertEqual(
			"https://sap.example.com/api/orders",
			build_url("https://sap.example.com/", "/api/orders"),
		)

	def test_returns_the_base_url_unchanged_when_no_path_is_given(self) -> None:
		self.assertEqual("https://sap.example.com", build_url("https://sap.example.com", None))
		self.assertEqual("https://sap.example.com", build_url("https://sap.example.com", ""))


class TestOauthCacheTtl(unittest.TestCase):
	def test_subtracts_the_safety_margin_from_a_sufficient_ttl(self) -> None:
		self.assertEqual(270, oauth_cache_ttl_seconds(300, safety_margin_seconds=30))

	def test_refuses_to_cache_when_ttl_does_not_clear_the_safety_margin(self) -> None:
		self.assertIsNone(oauth_cache_ttl_seconds(30, safety_margin_seconds=30))
		self.assertIsNone(oauth_cache_ttl_seconds(10, safety_margin_seconds=30))

	def test_refuses_to_cache_a_zero_or_negative_ttl(self) -> None:
		self.assertIsNone(oauth_cache_ttl_seconds(0, safety_margin_seconds=30))


if __name__ == "__main__":
	unittest.main()
