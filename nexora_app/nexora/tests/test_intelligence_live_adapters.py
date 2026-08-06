from __future__ import annotations

from unittest import TestCase, mock

from nexora.intelligence.core import AdapterInvocationError, ProviderRequest
from nexora.intelligence.providers.anthropic_live import AnthropicLiveAdapter
from nexora.intelligence.providers.cohere_live import CohereLiveAdapter
from nexora.intelligence.providers.deepseek_live import DeepSeekLiveAdapter
from nexora.intelligence.providers.gemini_live import GeminiLiveAdapter
from nexora.intelligence.providers.groq_live import GroqLiveAdapter
from nexora.intelligence.providers.mistral_live import MistralLiveAdapter
from nexora.intelligence.providers.openai_live import OpenAILiveAdapter
from nexora.intelligence.providers.openrouter_live import OpenRouterLiveAdapter
from nexora.intelligence.providers.perplexity_live import PerplexityLiveAdapter

_SECRET = "sk-synthetic-1234567890abcdef1234567890"


def _kwargs(**overrides) -> dict:
	base = dict(api_key=_SECRET, default_model="test-model", timeout_seconds=30, temperature=0.2, max_tokens=1024)
	base.update(overrides)
	return base


class TestOpenAICompatibleAdaptersShareBehavior(TestCase):
	"""Un caso por adaptador compatible con OpenAI, más las pruebas de forma
	de solicitud una sola vez (heredadas de la base compartida) — no se
	repite la construcción de la solicitud seis veces (Capítulo 44)."""

	ADAPTERS = (
		(OpenAILiveAdapter, "openai", "https://api.openai.com/v1"),
		(GroqLiveAdapter, "groq", "https://api.groq.com/openai/v1"),
		(DeepSeekLiveAdapter, "deepseek", "https://api.deepseek.com/v1"),
		(MistralLiveAdapter, "mistral", "https://api.mistral.ai/v1"),
		(PerplexityLiveAdapter, "perplexity", "https://api.perplexity.ai"),
		(OpenRouterLiveAdapter, "openrouter", "https://openrouter.ai/api/v1"),
	)

	def test_each_adapter_declares_the_expected_provider_key_and_base_url(self) -> None:
		for cls, provider_key, base_url in self.ADAPTERS:
			with self.subTest(cls=cls.__name__):
				self.assertEqual(provider_key, cls.provider_key)
				self.assertEqual(base_url, cls.base_url)

	def test_each_adapter_sends_a_bearer_token_to_its_own_chat_completions_url(self) -> None:
		for cls, provider_key, base_url in self.ADAPTERS:
			with self.subTest(cls=cls.__name__):
				adapter = cls(**_kwargs())
				target = "nexora.intelligence.providers.openai_compatible_live.send_json_request"
				with mock.patch(target, return_value={"id": "resp-1"}) as sender:
					response = adapter.invoke(
						ProviderRequest(capability="text", payload={"prompt": "hola"}, correlation_id="c-1")
					)
				sender.assert_called_once()
				call = sender.call_args.kwargs
				self.assertEqual(f"{base_url}/chat/completions", call["url"])
				self.assertEqual(f"Bearer {_SECRET}", call["headers"]["Authorization"])
				self.assertEqual("test-model", call["payload"]["model"])
				self.assertEqual(provider_key, call["provider_key"])
				self.assertEqual(provider_key, response.provider_key)
				self.assertEqual({"id": "resp-1"}, response.data)

	def test_rejects_unsupported_capability_without_any_network_call(self) -> None:
		adapter = GroqLiveAdapter(**_kwargs())  # groq solo declara "text"
		with mock.patch(
			"nexora.intelligence.providers.openai_compatible_live.send_json_request"
		) as sender:
			with self.assertRaises(AdapterInvocationError):
				adapter.invoke(
					ProviderRequest(capability="vision", payload={}, correlation_id="c-2")
				)
		sender.assert_not_called()

	def test_uses_explicit_model_from_payload_over_the_default(self) -> None:
		adapter = OpenAILiveAdapter(**_kwargs(default_model="fallback-model"))
		with mock.patch(
			"nexora.intelligence.providers.openai_compatible_live.send_json_request",
			return_value={},
		) as sender:
			adapter.invoke(
				ProviderRequest(
					capability="text", payload={"prompt": "hola", "model": "explicit-model"}, correlation_id="c-3"
				)
			)
		self.assertEqual("explicit-model", sender.call_args.kwargs["payload"]["model"])

	def test_raises_without_network_call_when_no_model_is_configured(self) -> None:
		adapter = OpenAILiveAdapter(**_kwargs(default_model=""))
		with mock.patch(
			"nexora.intelligence.providers.openai_compatible_live.send_json_request"
		) as sender:
			with self.assertRaises(AdapterInvocationError):
				adapter.invoke(ProviderRequest(capability="text", payload={}, correlation_id="c-4"))
		sender.assert_not_called()


class TestAnthropicLiveAdapter(TestCase):
	def test_sends_x_api_key_header_and_anthropic_version(self) -> None:
		adapter = AnthropicLiveAdapter(**_kwargs())
		with mock.patch(
			"nexora.intelligence.providers.anthropic_live.send_json_request", return_value={"id": "msg_1"}
		) as sender:
			response = adapter.invoke(
				ProviderRequest(capability="text", payload={"prompt": "hola"}, correlation_id="c-5")
			)
		call = sender.call_args.kwargs
		self.assertEqual("https://api.anthropic.com/v1/messages", call["url"])
		self.assertEqual(_SECRET, call["headers"]["x-api-key"])
		self.assertIn("anthropic-version", call["headers"])
		self.assertNotIn("Authorization", call["headers"])
		self.assertEqual("anthropic", response.provider_key)

	def test_rejects_unsupported_capability_without_network_call(self) -> None:
		adapter = AnthropicLiveAdapter(**_kwargs())
		with mock.patch("nexora.intelligence.providers.anthropic_live.send_json_request") as sender:
			with self.assertRaises(AdapterInvocationError):
				adapter.invoke(ProviderRequest(capability="embedding", payload={}, correlation_id="c-6"))
		sender.assert_not_called()


class TestGeminiLiveAdapter(TestCase):
	def test_sends_x_goog_api_key_header_never_in_the_url(self) -> None:
		adapter = GeminiLiveAdapter(**_kwargs(default_model="gemini-pro"))
		with mock.patch(
			"nexora.intelligence.providers.gemini_live.send_json_request", return_value={"candidates": []}
		) as sender:
			response = adapter.invoke(
				ProviderRequest(capability="text", payload={"prompt": "hola"}, correlation_id="c-7")
			)
		call = sender.call_args.kwargs
		self.assertEqual(
			"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent", call["url"]
		)
		self.assertNotIn(_SECRET, call["url"])
		self.assertEqual(_SECRET, call["headers"]["x-goog-api-key"])
		self.assertEqual("gemini", response.provider_key)

	def test_supports_audio_capability(self) -> None:
		adapter = GeminiLiveAdapter(**_kwargs())
		with mock.patch(
			"nexora.intelligence.providers.gemini_live.send_json_request", return_value={}
		) as sender:
			adapter.invoke(ProviderRequest(capability="audio", payload={}, correlation_id="c-8"))
		sender.assert_called_once()


class TestCohereLiveAdapter(TestCase):
	def test_text_capability_uses_the_chat_endpoint(self) -> None:
		adapter = CohereLiveAdapter(**_kwargs())
		with mock.patch(
			"nexora.intelligence.providers.cohere_live.send_json_request", return_value={"text": "hola"}
		) as sender:
			adapter.invoke(ProviderRequest(capability="text", payload={"prompt": "hola"}, correlation_id="c-9"))
		self.assertEqual("https://api.cohere.com/v1/chat", sender.call_args.kwargs["url"])

	def test_embedding_capability_uses_the_embed_endpoint(self) -> None:
		adapter = CohereLiveAdapter(**_kwargs())
		with mock.patch(
			"nexora.intelligence.providers.cohere_live.send_json_request", return_value={"embeddings": []}
		) as sender:
			adapter.invoke(
				ProviderRequest(capability="embedding", payload={"texts": ["hola"]}, correlation_id="c-10")
			)
		call = sender.call_args.kwargs
		self.assertEqual("https://api.cohere.com/v1/embed", call["url"])
		self.assertEqual(["hola"], call["payload"]["texts"])

	def test_rejects_unsupported_capability_without_network_call(self) -> None:
		adapter = CohereLiveAdapter(**_kwargs())
		with mock.patch("nexora.intelligence.providers.cohere_live.send_json_request") as sender:
			with self.assertRaises(AdapterInvocationError):
				adapter.invoke(ProviderRequest(capability="vision", payload={}, correlation_id="c-11"))
		sender.assert_not_called()
