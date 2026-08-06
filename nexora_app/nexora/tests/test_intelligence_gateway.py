from __future__ import annotations

from unittest import TestCase

from nexora.intelligence.adapters import AdapterRegistry
from nexora.intelligence.core import (
	NoProviderAvailableError,
	ProviderConfigError,
	ProviderNotFoundError,
	ProviderRequest,
	ProviderResponse,
)
from nexora.intelligence.gateway import build_registry, dispatch, resolve


def _row(key: str, *, status: str = "Active", capabilities="text", priority: int = 100) -> dict:
	return {
		"provider_key": key,
		"display_name": key.title(),
		"status": status,
		"capabilities": capabilities,
		"priority": priority,
	}


class TestBuildRegistry(TestCase):
	def test_builds_registry_from_rows(self) -> None:
		registry = build_registry([_row("openai"), _row("anthropic")])
		self.assertEqual(2, len(registry))
		self.assertTrue(registry.get("openai").is_active)

	def test_parses_comma_separated_capabilities_from_row(self) -> None:
		registry = build_registry([_row("openai", capabilities="text,vision")])
		self.assertEqual(("text", "vision"), registry.get("openai").capabilities)

	def test_builds_empty_registry_from_no_rows(self) -> None:
		registry = build_registry([])
		self.assertEqual(0, len(registry))

	def test_revalidates_and_rejects_a_corrupt_row(self) -> None:
		with self.assertRaises(ProviderConfigError):
			build_registry([_row("openai", status="Pending")])


class TestGatewayResolve(TestCase):
	def test_resolves_the_expected_provider_end_to_end(self) -> None:
		rows = [_row("slow", priority=200), _row("fast", priority=1)]
		record = resolve(rows, "text")
		self.assertEqual("fast", record.provider_key)

	def test_resolve_honors_prefer(self) -> None:
		rows = [_row("fast", priority=1), _row("preferred", priority=999)]
		record = resolve(rows, "text", prefer="preferred")
		self.assertEqual("preferred", record.provider_key)

	def test_resolve_raises_no_provider_available_with_no_rows(self) -> None:
		with self.assertRaises(NoProviderAvailableError):
			resolve([], "text")

	def test_resolve_raises_no_provider_available_when_capability_unmatched(self) -> None:
		rows = [_row("text-only", capabilities="text")]
		with self.assertRaises(NoProviderAvailableError):
			resolve(rows, "vision")

	def test_resolve_ignores_inactive_rows(self) -> None:
		rows = [_row("inactive", status="Inactive", priority=1), _row("active", priority=999)]
		record = resolve(rows, "text")
		self.assertEqual("active", record.provider_key)


class _FakeAdapter:
	"""Doble de prueba mínimo: no depende de ``AIProviderAdapter`` ni de los
	stubs reales del Bloque 2, para que estas pruebas de ``dispatch`` sean
	hermas frente a qué adaptadores estén registrados globalmente."""

	def __init__(self, provider_key: str) -> None:
		self.provider_key = provider_key
		self.capabilities = ("text",)
		self.received: ProviderRequest | None = None

	def invoke(self, request: ProviderRequest) -> ProviderResponse:
		self.received = request
		return ProviderResponse(
			provider_key=self.provider_key,
			capability=request.capability,
			data={"handled_by": self.provider_key},
		)


class TestGatewayDispatch(TestCase):
	def test_dispatch_resolves_and_invokes_the_matching_adapter(self) -> None:
		rows = [_row("fake")]
		adapters = AdapterRegistry([_FakeAdapter("fake")])
		response = dispatch(rows, "text", {"prompt": "hola"}, "corr-1", adapters=adapters)
		self.assertEqual("fake", response.provider_key)
		self.assertEqual({"handled_by": "fake"}, response.data)

	def test_dispatch_passes_the_exact_payload_and_correlation_id_through(self) -> None:
		rows = [_row("fake")]
		fake = _FakeAdapter("fake")
		adapters = AdapterRegistry([fake])
		dispatch(rows, "text", {"prompt": "hola"}, "corr-2", adapters=adapters)
		self.assertIsNotNone(fake.received)
		self.assertEqual({"prompt": "hola"}, fake.received.payload)
		self.assertEqual("corr-2", fake.received.correlation_id)
		self.assertEqual("text", fake.received.capability)

	def test_dispatch_raises_no_provider_available_when_nothing_is_configured(self) -> None:
		with self.assertRaises(NoProviderAvailableError):
			dispatch([], "text", {}, "corr-3", adapters=AdapterRegistry())

	def test_dispatch_raises_provider_not_found_when_configured_but_no_adapter_exists(self) -> None:
		# "ghost" está configurado y activo (Bloque 1) pero no tiene ningún
		# adaptador de código registrado (Bloque 2) — situación válida, no un
		# defecto: la configuración no obliga a que exista implementación.
		rows = [_row("ghost")]
		with self.assertRaises(ProviderNotFoundError):
			dispatch(rows, "text", {}, "corr-4", adapters=AdapterRegistry())

	def test_dispatch_honors_prefer(self) -> None:
		rows = [_row("fast", priority=1), _row("preferred", priority=999)]
		adapters = AdapterRegistry([_FakeAdapter("fast"), _FakeAdapter("preferred")])
		response = dispatch(rows, "text", {}, "corr-5", prefer="preferred", adapters=adapters)
		self.assertEqual("preferred", response.provider_key)

	def test_dispatch_uses_the_real_block_2_stub_adapters_by_default(self) -> None:
		rows = [_row("openai", capabilities="text,vision")]
		response = dispatch(rows, "text", {"prompt": "hola"}, "corr-6")
		self.assertEqual("openai", response.provider_key)
		self.assertTrue(response.data["simulated"])
