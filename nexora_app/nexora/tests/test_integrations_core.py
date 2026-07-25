from __future__ import annotations

from unittest import TestCase

from nexora.integrations.core import (
	INTEGRATION_STATUSES,
	IntegrationError,
	redact_credentials,
	validate_endpoint,
)


class TestIntegrationsCore(TestCase):
	def test_integration_statuses_are_correct(self) -> None:
		self.assertIn("Active", INTEGRATION_STATUSES)
		self.assertIn("Inactive", INTEGRATION_STATUSES)
		self.assertIn("Error", INTEGRATION_STATUSES)
		self.assertIn("Disabled", INTEGRATION_STATUSES)
		self.assertEqual(4, len(INTEGRATION_STATUSES))

	def test_validate_endpoint_valid_https(self) -> None:
		try:
			validate_endpoint("https://api.example.com/v1")
		except IntegrationError:
			self.fail("URL HTTPS valida no deberia fallar")

	def test_validate_endpoint_valid_http(self) -> None:
		try:
			validate_endpoint("http://localhost:8000")
		except IntegrationError:
			self.fail("URL HTTP valida no deberia fallar")

	def test_validate_endpoint_invalid_no_scheme_raises(self) -> None:
		with self.assertRaises(IntegrationError):
			validate_endpoint("not-a-url")

	def test_validate_endpoint_invalid_empty_raises(self) -> None:
		with self.assertRaises(IntegrationError):
			validate_endpoint("")

	def test_validate_endpoint_invalid_random_text_raises(self) -> None:
		with self.assertRaises(IntegrationError):
			validate_endpoint("foo bar baz")

	def test_redact_credentials_hides_token(self) -> None:
		text = "Authorization: Bearer sk-1234567890abcdef"
		result = redact_credentials(text)
		self.assertIn("***REDACTED***", result)
		self.assertNotIn("sk-1234567890abcdef", result)

	def test_redact_credentials_hides_password(self) -> None:
		text = 'password = "supersecret123"'
		result = redact_credentials(text)
		self.assertIn("***REDACTED***", result)
		self.assertNotIn("supersecret123", result)

	def test_redact_credentials_hides_api_key(self) -> None:
		text = "api_key: abcdef123456"
		result = redact_credentials(text)
		self.assertIn("***REDACTED***", result)
		self.assertNotIn("abcdef123456", result)

	def test_redact_credentials_passes_clean_text(self) -> None:
		text = '{"status": "ok", "message": "hello"}'
		result = redact_credentials(text)
		self.assertEqual(text, result)

	def test_redact_credentials_hides_secret(self) -> None:
		text = "client_secret=myverylongsecretvalue"
		result = redact_credentials(text)
		self.assertIn("***REDACTED***", result)
		self.assertNotIn("myverylongsecretvalue", result)
