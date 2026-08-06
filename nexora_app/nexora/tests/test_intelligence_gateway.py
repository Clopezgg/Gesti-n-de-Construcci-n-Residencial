from __future__ import annotations

from unittest import TestCase

from nexora.intelligence.core import NoProviderAvailableError, ProviderConfigError
from nexora.intelligence.gateway import build_registry, resolve


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
