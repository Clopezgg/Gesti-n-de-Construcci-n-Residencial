from __future__ import annotations

from unittest import TestCase

from nexora.intelligence.core import (
	AdapterInvocationError,
	CredentialNotConfiguredError,
	ProviderConfigError,
	ProviderDisabledError,
	ProviderNotFoundError,
)
from nexora.intelligence.providers.anthropic_live import AnthropicLiveAdapter
from nexora.intelligence.providers.cohere_live import CohereLiveAdapter
from nexora.intelligence.providers.openai_live import OpenAILiveAdapter
from nexora.intelligence.runtime_core import REAL_ADAPTER_CLASSES, check_readiness, prepare_adapter

_SECRET = "sk-synthetic-1234567890abcdef1234567890"


def _row(**overrides) -> dict:
	base = {
		"provider_key": "openai",
		"status": "Active",
		"capabilities": "text,vision",
		"default_model": "gpt-4o-mini",
		"timeout_seconds": 30,
		"temperature": 0.2,
		"max_tokens": 1024,
	}
	base.update(overrides)
	return base


class TestRealAdapterClasses(TestCase):
	def test_covers_exactly_the_nine_official_providers(self) -> None:
		self.assertEqual(
			{
				"openai",
				"anthropic",
				"gemini",
				"groq",
				"deepseek",
				"mistral",
				"cohere",
				"perplexity",
				"openrouter",
			},
			set(REAL_ADAPTER_CLASSES),
		)

	def test_openai_maps_to_the_expected_class(self) -> None:
		self.assertIs(OpenAILiveAdapter, REAL_ADAPTER_CLASSES["openai"])

	def test_anthropic_maps_to_the_expected_class(self) -> None:
		self.assertIs(AnthropicLiveAdapter, REAL_ADAPTER_CLASSES["anthropic"])

	def test_cohere_maps_to_the_expected_class(self) -> None:
		self.assertIs(CohereLiveAdapter, REAL_ADAPTER_CLASSES["cohere"])


class TestCheckReadiness(TestCase):
	def test_ready_when_everything_is_configured(self) -> None:
		report = check_readiness(_row(), _SECRET)
		self.assertTrue(report["ready"])
		self.assertEqual([], report["reasons"])
		self.assertTrue(report["has_credential"])

	def test_not_ready_when_disabled(self) -> None:
		report = check_readiness(_row(status="Inactive"), _SECRET)
		self.assertFalse(report["ready"])
		self.assertTrue(any("Active" in reason for reason in report["reasons"]))

	def test_not_ready_when_missing_default_model(self) -> None:
		report = check_readiness(_row(default_model=""), _SECRET)
		self.assertFalse(report["ready"])
		self.assertTrue(any("modelo" in reason for reason in report["reasons"]))

	def test_not_ready_when_missing_credential(self) -> None:
		report = check_readiness(_row(), None)
		self.assertFalse(report["ready"])
		self.assertFalse(report["has_credential"])

	def test_not_ready_when_capability_unsupported(self) -> None:
		report = check_readiness(_row(capabilities="text"), _SECRET, capability="audio")
		self.assertFalse(report["ready"])
		self.assertTrue(any("audio" in reason for reason in report["reasons"]))

	def test_not_ready_for_unknown_provider_key(self) -> None:
		report = check_readiness(_row(provider_key="not-a-real-provider"), _SECRET)
		self.assertFalse(report["ready"])

	def test_ready_report_never_includes_the_secret(self) -> None:
		report = check_readiness(_row(), _SECRET)
		self.assertNotIn(_SECRET, str(report))

	def test_accumulates_multiple_reasons_at_once(self) -> None:
		report = check_readiness(_row(status="Disabled", default_model=""), None)
		self.assertGreaterEqual(len(report["reasons"]), 3)


class TestPrepareAdapter(TestCase):
	def test_builds_a_ready_adapter_when_everything_is_configured(self) -> None:
		adapter = prepare_adapter(_row(), _SECRET)
		self.assertIsInstance(adapter, OpenAILiveAdapter)

	def test_raises_provider_disabled_when_not_active(self) -> None:
		with self.assertRaises(ProviderDisabledError):
			prepare_adapter(_row(status="Inactive"), _SECRET)

	def test_raises_adapter_invocation_error_for_unsupported_capability(self) -> None:
		with self.assertRaises(AdapterInvocationError):
			prepare_adapter(_row(capabilities="text"), _SECRET, capability="audio")

	def test_raises_provider_config_error_without_default_model(self) -> None:
		with self.assertRaises(ProviderConfigError):
			prepare_adapter(_row(default_model=""), _SECRET)

	def test_raises_credential_not_configured_without_a_secret(self) -> None:
		with self.assertRaises(CredentialNotConfiguredError):
			prepare_adapter(_row(), None)

	def test_raises_credential_not_configured_with_an_empty_secret(self) -> None:
		with self.assertRaises(CredentialNotConfiguredError):
			prepare_adapter(_row(), "")

	def test_raises_provider_not_found_for_unknown_provider_key(self) -> None:
		with self.assertRaises(ProviderNotFoundError):
			prepare_adapter(_row(provider_key="not-a-real-provider"), _SECRET)

	def test_falls_back_to_config_defaults_when_row_omits_them(self) -> None:
		minimal_row = {
			"provider_key": "openai",
			"status": "Active",
			"capabilities": "text",
			"default_model": "gpt-4o-mini",
		}
		adapter = prepare_adapter(minimal_row, _SECRET)
		self.assertIsInstance(adapter, OpenAILiveAdapter)

	def test_disabled_check_runs_before_credential_check(self) -> None:
		# Un proveedor deshabilitado debe fallar por eso, no confundirse con
		# "sin credencial" aunque también le falte la credencial.
		with self.assertRaises(ProviderDisabledError):
			prepare_adapter(_row(status="Disabled"), None)
