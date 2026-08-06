from __future__ import annotations

import pathlib
import unittest
from unittest import TestCase

import nexora
from nexora.intelligence.core import AdapterInvocationError, AIProviderAdapter, ProviderRequest
from nexora.intelligence.providers.anthropic_stub import AnthropicStubAdapter
from nexora.intelligence.providers.cohere_stub import CohereAdapter
from nexora.intelligence.providers.deepseek_stub import DeepSeekAdapter
from nexora.intelligence.providers.gemini_stub import GeminiStubAdapter
from nexora.intelligence.providers.groq_stub import GroqAdapter
from nexora.intelligence.providers.mistral_stub import MistralAdapter
from nexora.intelligence.providers.openai_stub import OpenAIStubAdapter
from nexora.intelligence.providers.openrouter_stub import OpenRouterAdapter
from nexora.intelligence.providers.perplexity_stub import PerplexityAdapter

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent
PROVIDERS_DIR = APP_ROOT / "intelligence/providers"

# Bloque 2.
STUB_ADAPTERS = (
	("openai", OpenAIStubAdapter, ("text", "vision")),
	("anthropic", AnthropicStubAdapter, ("text", "vision")),
	("gemini", GeminiStubAdapter, ("text", "vision", "audio")),
)

# Bloque 2.1 — mismo contrato, seis proveedores más.
EXPANDED_STUB_ADAPTERS = (
	("groq", GroqAdapter, ("text",)),
	("deepseek", DeepSeekAdapter, ("text",)),
	("mistral", MistralAdapter, ("text", "vision")),
	("cohere", CohereAdapter, ("text", "embedding")),
	("perplexity", PerplexityAdapter, ("text",)),
	("openrouter", OpenRouterAdapter, ("text", "vision")),
)

ALL_STUB_ADAPTERS = STUB_ADAPTERS + EXPANDED_STUB_ADAPTERS


class TestStubAdaptersSatisfyTheContract(TestCase):
	def test_each_stub_is_an_ai_provider_adapter(self) -> None:
		for _, cls, _capabilities in ALL_STUB_ADAPTERS:
			with self.subTest(cls=cls.__name__):
				self.assertTrue(issubclass(cls, AIProviderAdapter))
				self.assertIsInstance(cls(), AIProviderAdapter)

	def test_each_stub_declares_its_provider_key(self) -> None:
		for key, cls, _capabilities in ALL_STUB_ADAPTERS:
			with self.subTest(cls=cls.__name__):
				self.assertEqual(key, cls().provider_key)

	def test_each_stub_declares_the_expected_capabilities(self) -> None:
		for _key, cls, capabilities in ALL_STUB_ADAPTERS:
			with self.subTest(cls=cls.__name__):
				self.assertEqual(capabilities, cls().capabilities)


class TestStubAdaptersInvoke(TestCase):
	def test_invoke_returns_a_simulated_response_for_a_supported_capability(self) -> None:
		adapter = OpenAIStubAdapter()
		request = ProviderRequest(capability="text", payload={"prompt": "hola"}, correlation_id="corr-1")
		response = adapter.invoke(request)
		self.assertEqual("openai", response.provider_key)
		self.assertEqual("text", response.capability)
		self.assertTrue(response.data["simulated"])
		self.assertEqual({"prompt": "hola"}, response.data["echo"])
		self.assertEqual("corr-1", response.data["correlation_id"])

	def test_invoke_never_claims_to_be_real(self) -> None:
		for _key, cls, capabilities in ALL_STUB_ADAPTERS:
			with self.subTest(cls=cls.__name__):
				adapter = cls()
				request = ProviderRequest(
					capability=capabilities[0], payload={}, correlation_id="corr-2"
				)
				response = adapter.invoke(request)
				self.assertTrue(response.data["simulated"])

	def test_invoke_rejects_an_unsupported_capability(self) -> None:
		adapter = OpenAIStubAdapter()
		# "audio" no está en las capacidades declaradas por el stub de OpenAI.
		request = ProviderRequest(capability="audio", payload={}, correlation_id="corr-3")
		with self.assertRaises(AdapterInvocationError):
			adapter.invoke(request)

	def test_invoke_is_deterministic_for_the_same_input(self) -> None:
		adapter = GeminiStubAdapter()
		request = ProviderRequest(capability="audio", payload={"a": 1}, correlation_id="corr-4")
		first = adapter.invoke(request)
		second = adapter.invoke(request)
		self.assertEqual(first.data, second.data)

	def test_invoke_echoes_the_exact_payload_without_mutating_it(self) -> None:
		adapter = AnthropicStubAdapter()
		payload = {"prompt": "hola", "nested": {"x": 1}}
		request = ProviderRequest(capability="text", payload=payload, correlation_id="corr-5")
		response = adapter.invoke(request)
		self.assertEqual(payload, response.data["echo"])
		self.assertEqual({"prompt": "hola", "nested": {"x": 1}}, payload)

	def test_groq_rejects_vision_it_never_declared(self) -> None:
		adapter = GroqAdapter()
		request = ProviderRequest(capability="vision", payload={}, correlation_id="corr-6")
		with self.assertRaises(AdapterInvocationError):
			adapter.invoke(request)

	def test_cohere_accepts_embedding_and_returns_it_simulated(self) -> None:
		adapter = CohereAdapter()
		request = ProviderRequest(capability="embedding", payload={"text": "hola"}, correlation_id="corr-7")
		response = adapter.invoke(request)
		self.assertEqual("embedding", response.capability)
		self.assertTrue(response.data["simulated"])

	def test_openrouter_rejects_audio_it_never_declared(self) -> None:
		adapter = OpenRouterAdapter()
		request = ProviderRequest(capability="audio", payload={}, correlation_id="corr-8")
		with self.assertRaises(AdapterInvocationError):
			adapter.invoke(request)


class TestStubsDoNotTouchRealProviders(TestCase):
	"""Bloque 2: adaptadores simulados. Ninguno debe importar un SDK real,
	un cliente HTTP o abrir una conexión de red."""

	FORBIDDEN_TOKENS = (
		"import openai",
		"import anthropic",
		"google.generativeai",
		"import requests",
		"import httpx",
		"urllib.request",
		"http.client",
		"socket.",
		"aiohttp",
	)

	def test_provider_stub_files_exist(self) -> None:
		for relative in (
			"providers/__init__.py",
			"providers/stub_support.py",
			"providers/openai_stub.py",
			"providers/anthropic_stub.py",
			"providers/gemini_stub.py",
		):
			self.assertTrue((APP_ROOT / "intelligence" / relative).is_file(), relative)

	def test_block_2_1_provider_stub_files_exist(self) -> None:
		for relative in (
			"providers/groq_stub.py",
			"providers/deepseek_stub.py",
			"providers/mistral_stub.py",
			"providers/cohere_stub.py",
			"providers/perplexity_stub.py",
			"providers/openrouter_stub.py",
		):
			self.assertTrue((APP_ROOT / "intelligence" / relative).is_file(), relative)

	def test_no_provider_file_imports_a_real_sdk_or_touches_the_network(self) -> None:
		offenders: list[str] = []
		for path in sorted(PROVIDERS_DIR.glob("*.py")):
			source = path.read_text(encoding="utf-8")
			for token in self.FORBIDDEN_TOKENS:
				if token in source:
					offenders.append(f"{path.name}: {token}")
		self.assertEqual([], offenders)

	def test_adapters_module_does_not_import_a_real_sdk(self) -> None:
		source = (APP_ROOT / "intelligence/adapters.py").read_text(encoding="utf-8")
		for token in self.FORBIDDEN_TOKENS:
			self.assertNotIn(token, source)


if __name__ == "__main__":
	unittest.main()
