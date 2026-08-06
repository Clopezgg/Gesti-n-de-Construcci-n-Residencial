from __future__ import annotations

from unittest import TestCase

from nexora.intelligence import adapters as adapters_module
from nexora.intelligence.adapters import (
	AdapterRegistry,
	build_default_registry,
	known_adapter_keys,
	register_adapter,
)
from nexora.intelligence.core import AIProviderAdapter, ProviderNotFoundError, ProviderRequest, ProviderResponse


class _StubAdapter(AIProviderAdapter):
	provider_key = "unit-test-stub"
	capabilities = ("text",)

	def invoke(self, request: ProviderRequest) -> ProviderResponse:
		return ProviderResponse(provider_key=self.provider_key, capability=request.capability, data={})


class TestRegisterAdapter(TestCase):
	def tearDown(self) -> None:
		# ``register_adapter`` escribe en un diccionario a nivel de módulo,
		# compartido por todo el proceso de pruebas. Limpiar la clave de
		# prueba evita que se filtre a ``build_default_registry()`` en otros
		# archivos de prueba que corran en el mismo proceso.
		adapters_module._ADAPTER_CLASSES.pop("unit-test-stub", None)

	def test_registers_class_under_its_provider_key(self) -> None:
		register_adapter(_StubAdapter)
		self.assertIn("unit-test-stub", known_adapter_keys())

	def test_returns_the_same_class_unchanged(self) -> None:
		result = register_adapter(_StubAdapter)
		self.assertIs(_StubAdapter, result)

	def test_re_registering_the_same_class_is_idempotent(self) -> None:
		register_adapter(_StubAdapter)
		register_adapter(_StubAdapter)  # no debe lanzar
		self.assertIn("unit-test-stub", known_adapter_keys())

	def test_rejects_class_without_provider_key(self) -> None:
		class NoKeyAdapter(AIProviderAdapter):
			provider_key = ""
			capabilities = ("text",)

			def invoke(self, request: ProviderRequest) -> ProviderResponse:
				raise NotImplementedError

		with self.assertRaises(ValueError):
			register_adapter(NoKeyAdapter)

	def test_rejects_a_different_class_reusing_an_existing_key(self) -> None:
		register_adapter(_StubAdapter)

		class ConflictingAdapter(AIProviderAdapter):
			provider_key = "unit-test-stub"
			capabilities = ("text",)

			def invoke(self, request: ProviderRequest) -> ProviderResponse:
				raise NotImplementedError

		with self.assertRaises(ValueError):
			register_adapter(ConflictingAdapter)


class TestAdapterRegistry(TestCase):
	def test_starts_empty(self) -> None:
		registry = AdapterRegistry()
		self.assertEqual(0, len(registry))

	def test_register_and_get(self) -> None:
		registry = AdapterRegistry()
		instance = _StubAdapter()
		registry.register(instance)
		self.assertIs(instance, registry.get("unit-test-stub"))
		self.assertIn("unit-test-stub", registry)

	def test_constructor_accepts_initial_instances(self) -> None:
		registry = AdapterRegistry([_StubAdapter()])
		self.assertEqual(1, len(registry))

	def test_get_missing_raises_provider_not_found(self) -> None:
		registry = AdapterRegistry()
		with self.assertRaises(ProviderNotFoundError):
			registry.get("missing")

	def test_list_all_returns_every_registered_instance(self) -> None:
		registry = AdapterRegistry([_StubAdapter()])
		self.assertEqual(1, len(registry.list_all()))


class TestBuildDefaultRegistry(TestCase):
	def test_includes_the_three_block_2_stub_providers(self) -> None:
		registry = build_default_registry()
		for key in ("openai", "anthropic", "gemini"):
			self.assertIn(key, registry, key)

	def test_includes_the_six_block_2_1_stub_providers(self) -> None:
		registry = build_default_registry()
		for key in ("groq", "deepseek", "mistral", "cohere", "perplexity", "openrouter"):
			self.assertIn(key, registry, key)

	def test_default_registry_has_exactly_nine_providers_after_block_2_1(self) -> None:
		registry = build_default_registry()
		self.assertEqual(9, len(registry))

	def test_default_registry_is_a_fresh_instance_each_call(self) -> None:
		first = build_default_registry()
		second = build_default_registry()
		self.assertIsNot(first, second)
		self.assertIsNot(first.get("openai"), second.get("openai"))
