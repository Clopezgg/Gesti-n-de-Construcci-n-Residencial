from __future__ import annotations

from unittest import TestCase

from nexora.intelligence.core import NoProviderAvailableError, ProviderConfigError, ProviderRecord
from nexora.intelligence.registry import ProviderRegistry
from nexora.intelligence.router import resolve_provider


def _record(
	key: str, *, status: str = "Active", capabilities=("text",), priority: int = 100
) -> ProviderRecord:
	return ProviderRecord(
		provider_key=key,
		display_name=key.title(),
		status=status,
		capabilities=capabilities,
		priority=priority,
	)


class TestResolveProvider(TestCase):
	def test_picks_the_only_active_matching_provider(self) -> None:
		registry = ProviderRegistry([_record("openai")])
		resolved = resolve_provider(registry, "text")
		self.assertEqual("openai", resolved.provider_key)

	def test_picks_lowest_priority_number_first(self) -> None:
		registry = ProviderRegistry([_record("slow", priority=200), _record("fast", priority=10)])
		resolved = resolve_provider(registry, "text")
		self.assertEqual("fast", resolved.provider_key)

	def test_breaks_ties_by_provider_key_for_determinism(self) -> None:
		registry = ProviderRegistry([_record("zeta", priority=10), _record("alpha", priority=10)])
		resolved = resolve_provider(registry, "text")
		self.assertEqual("alpha", resolved.provider_key)

	def test_is_deterministic_across_repeated_calls(self) -> None:
		registry = ProviderRegistry(
			[_record("zeta", priority=10), _record("alpha", priority=10), _record("mid", priority=50)]
		)
		results = {resolve_provider(registry, "text").provider_key for _ in range(5)}
		self.assertEqual({"alpha"}, results)

	def test_ignores_inactive_providers(self) -> None:
		registry = ProviderRegistry(
			[_record("inactive", status="Inactive", priority=1), _record("active", priority=999)]
		)
		resolved = resolve_provider(registry, "text")
		self.assertEqual("active", resolved.provider_key)

	def test_ignores_providers_without_the_capability(self) -> None:
		registry = ProviderRegistry(
			[_record("text-only", capabilities=("text",)), _record("vision-only", capabilities=("vision",))]
		)
		resolved = resolve_provider(registry, "vision")
		self.assertEqual("vision-only", resolved.provider_key)

	def test_prefer_wins_over_priority_when_active_and_capable(self) -> None:
		registry = ProviderRegistry([_record("fast", priority=1), _record("preferred", priority=999)])
		resolved = resolve_provider(registry, "text", prefer="preferred")
		self.assertEqual("preferred", resolved.provider_key)

	def test_prefer_falls_back_to_priority_when_preferred_is_inactive(self) -> None:
		registry = ProviderRegistry(
			[_record("preferred", status="Inactive"), _record("fallback", priority=5)]
		)
		resolved = resolve_provider(registry, "text", prefer="preferred")
		self.assertEqual("fallback", resolved.provider_key)

	def test_prefer_falls_back_when_preferred_does_not_support_capability(self) -> None:
		registry = ProviderRegistry(
			[_record("preferred", capabilities=("audio",)), _record("fallback", capabilities=("text",))]
		)
		resolved = resolve_provider(registry, "text", prefer="preferred")
		self.assertEqual("fallback", resolved.provider_key)

	def test_raises_when_no_active_provider_supports_capability(self) -> None:
		registry = ProviderRegistry([_record("text-only", capabilities=("text",))])
		with self.assertRaises(NoProviderAvailableError):
			resolve_provider(registry, "audio")

	def test_raises_when_registry_is_empty(self) -> None:
		registry = ProviderRegistry()
		with self.assertRaises(NoProviderAvailableError):
			resolve_provider(registry, "text")

	def test_raises_when_all_matching_providers_are_inactive(self) -> None:
		registry = ProviderRegistry([_record("openai", status="Disabled")])
		with self.assertRaises(NoProviderAvailableError):
			resolve_provider(registry, "text")

	def test_rejects_unknown_capability(self) -> None:
		registry = ProviderRegistry([_record("openai")])
		with self.assertRaises(ProviderConfigError):
			resolve_provider(registry, "telepathy")
