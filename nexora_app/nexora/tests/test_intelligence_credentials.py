from __future__ import annotations

import os
from unittest import TestCase, mock

from nexora.intelligence.core import CredentialFormatError
from nexora.intelligence.credentials import (
	PROVIDER_ENV_VARS,
	known_provider_env_var,
	resolve_environment_credential,
	validate_credential_format,
)

# Nunca un secreto real: valores sintéticos, deliberadamente sin ninguno de
# los marcadores de plantilla que `validate_credential_format` rechaza, y sin
# el prefijo `sk-` para no coincidir con el patrón `openai_key` de
# `scripts/scan_nexora_secrets.py` (el scanner no distingue una clave
# sintética de prueba de una real con la misma forma).
_VALID_SYNTHETIC_SECRET = "synthetic-test-secret-1234567890abcdef1234567890"


class TestProviderEnvVars(TestCase):
	def test_covers_exactly_the_nine_official_providers(self) -> None:
		self.assertEqual(
			{
				"anthropic",
				"openai",
				"perplexity",
				"openrouter",
				"gemini",
				"groq",
				"deepseek",
				"mistral",
				"cohere",
			},
			set(PROVIDER_ENV_VARS),
		)

	def test_env_var_names_match_the_official_names_exactly(self) -> None:
		self.assertEqual(
			{
				"anthropic": "ANTHROPIC_API_KEY",
				"openai": "OPENAI_API_KEY",
				"perplexity": "PERPLEXITY_API_KEY",
				"openrouter": "OPENROUTER_API_KEY",
				"gemini": "GEMINI_API_KEY",
				"groq": "GROQ_API_KEY",
				"deepseek": "DEEPSEEK_API_KEY",
				"mistral": "MISTRAL_API_KEY",
				"cohere": "COHERE_API_KEY",
			},
			PROVIDER_ENV_VARS,
		)

	def test_known_provider_env_var_returns_the_right_name(self) -> None:
		self.assertEqual("OPENAI_API_KEY", known_provider_env_var("openai"))

	def test_known_provider_env_var_returns_none_for_unknown_provider(self) -> None:
		self.assertIsNone(known_provider_env_var("not-a-real-provider"))


class TestValidateCredentialFormat(TestCase):
	def test_accepts_a_well_formed_synthetic_secret(self) -> None:
		self.assertEqual(_VALID_SYNTHETIC_SECRET, validate_credential_format(_VALID_SYNTHETIC_SECRET))

	def test_rejects_empty_string(self) -> None:
		with self.assertRaises(CredentialFormatError):
			validate_credential_format("")

	def test_rejects_non_string(self) -> None:
		with self.assertRaises(CredentialFormatError):
			validate_credential_format(None)  # type: ignore[arg-type]

	def test_rejects_leading_whitespace(self) -> None:
		with self.assertRaises(CredentialFormatError):
			validate_credential_format(" " + _VALID_SYNTHETIC_SECRET)

	def test_rejects_trailing_whitespace(self) -> None:
		with self.assertRaises(CredentialFormatError):
			validate_credential_format(_VALID_SYNTHETIC_SECRET + " ")

	def test_rejects_too_short(self) -> None:
		with self.assertRaises(CredentialFormatError):
			validate_credential_format("short")

	def test_rejects_too_long(self) -> None:
		with self.assertRaises(CredentialFormatError):
			validate_credential_format("x" * 257)

	def test_accepts_exactly_the_minimum_length(self) -> None:
		value = "a" * 16
		self.assertEqual(value, validate_credential_format(value))

	def test_accepts_exactly_the_maximum_length(self) -> None:
		value = "a" * 256
		self.assertEqual(value, validate_credential_format(value))

	def test_rejects_changeme_placeholder(self) -> None:
		with self.assertRaises(CredentialFormatError):
			validate_credential_format("changeme-1234567890abcdef")

	def test_rejects_reemplazar_placeholder(self) -> None:
		with self.assertRaises(CredentialFormatError):
			validate_credential_format("REEMPLAZAR_CON_UNA_CLAVE_REAL_1234")

	def test_rejects_your_api_key_placeholder(self) -> None:
		with self.assertRaises(CredentialFormatError):
			validate_credential_format("your-api-key-goes-right-here-1234")

	def test_rejects_placeholder_case_insensitively(self) -> None:
		with self.assertRaises(CredentialFormatError):
			validate_credential_format("SK-CHANGEME-1234567890ABCDEF")

	def test_error_message_never_echoes_the_rejected_value(self) -> None:
		secret = "short-but-suspicious-value"
		try:
			validate_credential_format(secret[:5])
		except CredentialFormatError as exc:
			self.assertNotIn(secret[:5], str(exc))
		else:
			self.fail("se esperaba CredentialFormatError")


class TestResolveEnvironmentCredential(TestCase):
	def test_reads_the_configured_env_var(self) -> None:
		with mock.patch.dict(os.environ, {"OPENAI_API_KEY": _VALID_SYNTHETIC_SECRET}, clear=False):
			self.assertEqual(_VALID_SYNTHETIC_SECRET, resolve_environment_credential("openai"))

	def test_returns_none_when_env_var_is_absent(self) -> None:
		with mock.patch.dict(os.environ, {}, clear=False):
			os.environ.pop("COHERE_API_KEY", None)
			self.assertIsNone(resolve_environment_credential("cohere"))

	def test_returns_none_when_env_var_is_blank(self) -> None:
		with mock.patch.dict(os.environ, {"GROQ_API_KEY": "   "}, clear=False):
			self.assertIsNone(resolve_environment_credential("groq"))

	def test_returns_none_for_a_provider_without_a_known_env_var(self) -> None:
		self.assertIsNone(resolve_environment_credential("not-a-real-provider"))

	def test_strips_surrounding_whitespace(self) -> None:
		with mock.patch.dict(os.environ, {"MISTRAL_API_KEY": f"  {_VALID_SYNTHETIC_SECRET}  "}, clear=False):
			self.assertEqual(_VALID_SYNTHETIC_SECRET, resolve_environment_credential("mistral"))
