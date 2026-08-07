from __future__ import annotations

from unittest import TestCase

from nexora.intelligence.core import ProviderNotFoundError, ProviderRecord
from nexora.intelligence.registry import ProviderRegistry


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


class TestProviderRegistry(TestCase):
	def test_starts_empty(self) -> None:
		registry = ProviderRegistry()
		self.assertEqual(0, len(registry))
		self.assertEqual((), registry.list_all())

	def test_register_and_get(self) -> None:
		registry = ProviderRegistry()
		record = _record("openai")
		registry.register(record)
		self.assertEqual(record, registry.get("openai"))
		self.assertIn("openai", registry)
		self.assertEqual(1, len(registry))

	def test_register_overwrites_same_key(self) -> None:
		registry = ProviderRegistry()
		registry.register(_record("openai", priority=100))
		registry.register(_record("openai", priority=5))
		self.assertEqual(1, len(registry))
		self.assertEqual(5, registry.get("openai").priority)

	def test_constructor_accepts_initial_records(self) -> None:
		registry = ProviderRegistry([_record("openai"), _record("anthropic")])
		self.assertEqual(2, len(registry))

	def test_get_missing_raises_provider_not_found(self) -> None:
		registry = ProviderRegistry()
		with self.assertRaises(ProviderNotFoundError):
			registry.get("missing")

	def test_unregister_removes_provider(self) -> None:
		registry = ProviderRegistry([_record("openai")])
		registry.unregister("openai")
		self.assertEqual(0, len(registry))
		self.assertNotIn("openai", registry)

	def test_unregister_unknown_key_is_a_no_op(self) -> None:
		registry = ProviderRegistry()
		registry.unregister("missing")
		self.assertEqual(0, len(registry))

	def test_list_active_excludes_inactive(self) -> None:
		registry = ProviderRegistry(
			[_record("openai", status="Active"), _record("anthropic", status="Inactive")]
		)
		active = registry.list_active()
		self.assertEqual(("openai",), tuple(r.provider_key for r in active))

	def test_list_by_capability_filters_and_defaults_to_active_only(self) -> None:
		registry = ProviderRegistry(
			[
				_record("openai", capabilities=("text", "vision")),
				_record("anthropic", capabilities=("text",)),
				_record("disabled-vision", status="Disabled", capabilities=("vision",)),
			]
		)
		vision_providers = registry.list_by_capability("vision")
		self.assertEqual(("openai",), tuple(r.provider_key for r in vision_providers))

	def test_list_by_capability_can_include_inactive(self) -> None:
		registry = ProviderRegistry([_record("disabled-vision", status="Disabled", capabilities=("vision",))])
		vision_providers = registry.list_by_capability("vision", active_only=False)
		self.assertEqual(("disabled-vision",), tuple(r.provider_key for r in vision_providers))

	def test_list_by_capability_with_no_match_returns_empty(self) -> None:
		registry = ProviderRegistry([_record("openai", capabilities=("text",))])
		self.assertEqual((), registry.list_by_capability("audio"))
