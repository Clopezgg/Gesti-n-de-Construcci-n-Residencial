from __future__ import annotations

from unittest import TestCase

from nexora.intelligence.core import (
	CAPABILITIES,
	PROVIDER_STATUSES,
	AIProviderAdapter,
	ProviderConfigError,
	ProviderRecord,
	ProviderRequest,
	ProviderResponse,
	parse_capabilities,
	validate_display_name,
	validate_priority,
	validate_provider_key,
	validate_status,
)


class TestConstants(TestCase):
	def test_provider_statuses_are_correct(self) -> None:
		self.assertEqual({"Active", "Inactive", "Error", "Disabled"}, set(PROVIDER_STATUSES))

	def test_capabilities_are_correct(self) -> None:
		self.assertEqual({"text", "vision", "audio", "embedding"}, set(CAPABILITIES))


class TestValidateProviderKey(TestCase):
	def test_accepts_simple_key(self) -> None:
		self.assertEqual("openai", validate_provider_key("openai"))

	def test_accepts_key_with_digits_and_separators(self) -> None:
		self.assertEqual("local-stub-2", validate_provider_key("local-stub-2"))

	def test_rejects_empty(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_provider_key("")

	def test_rejects_uppercase(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_provider_key("OpenAI")

	def test_rejects_leading_digit(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_provider_key("1provider")

	def test_rejects_spaces(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_provider_key("open ai")

	def test_rejects_single_character(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_provider_key("a")


class TestValidateDisplayName(TestCase):
	def test_accepts_trimmed_name(self) -> None:
		self.assertEqual("OpenAI GPT", validate_display_name("  OpenAI GPT  "))

	def test_rejects_empty(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_display_name("")

	def test_rejects_whitespace_only(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_display_name("   ")

	def test_rejects_too_long(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_display_name("x" * 141)


class TestValidateStatus(TestCase):
	def test_accepts_each_known_status(self) -> None:
		for status in PROVIDER_STATUSES:
			self.assertEqual(status, validate_status(status))

	def test_rejects_unknown_status(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_status("Pending")

	def test_rejects_lowercase_variant(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_status("active")


class TestValidatePriority(TestCase):
	def test_accepts_zero(self) -> None:
		self.assertEqual(0, validate_priority(0))

	def test_accepts_positive_int(self) -> None:
		self.assertEqual(50, validate_priority(50))

	def test_accepts_numeric_string(self) -> None:
		self.assertEqual(10, validate_priority("10"))

	def test_rejects_negative(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_priority(-1)

	def test_rejects_non_numeric(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_priority("high")

	def test_rejects_none(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_priority(None)


class TestParseCapabilities(TestCase):
	def test_parses_comma_separated_string(self) -> None:
		self.assertEqual(("text", "vision"), parse_capabilities("vision,text"))

	def test_parses_iterable(self) -> None:
		self.assertEqual(("audio", "text"), parse_capabilities(["text", "audio"]))

	def test_deduplicates_and_sorts(self) -> None:
		self.assertEqual(("text",), parse_capabilities("text,text, text"))

	def test_rejects_empty_string(self) -> None:
		with self.assertRaises(ProviderConfigError):
			parse_capabilities("")

	def test_rejects_empty_iterable(self) -> None:
		with self.assertRaises(ProviderConfigError):
			parse_capabilities([])

	def test_rejects_unknown_capability(self) -> None:
		with self.assertRaises(ProviderConfigError):
			parse_capabilities("text,telepathy")


class TestProviderRecord(TestCase):
	def _valid_kwargs(self) -> dict:
		return {
			"provider_key": "openai",
			"display_name": "OpenAI",
			"status": "Active",
			"capabilities": ("text", "vision"),
			"priority": 10,
		}

	def test_constructs_with_valid_data(self) -> None:
		record = ProviderRecord(**self._valid_kwargs())
		self.assertEqual("openai", record.provider_key)
		self.assertEqual(("text", "vision"), record.capabilities)
		self.assertTrue(record.is_active)

	def test_is_immutable(self) -> None:
		record = ProviderRecord(**self._valid_kwargs())
		with self.assertRaises(AttributeError):
			record.status = "Disabled"  # type: ignore[misc]

	def test_normalizes_display_name_whitespace(self) -> None:
		kwargs = self._valid_kwargs()
		kwargs["display_name"] = "  OpenAI  "
		record = ProviderRecord(**kwargs)
		self.assertEqual("OpenAI", record.display_name)

	def test_normalizes_capabilities_from_string(self) -> None:
		kwargs = self._valid_kwargs()
		kwargs["capabilities"] = "vision,text"
		record = ProviderRecord(**kwargs)
		self.assertEqual(("text", "vision"), record.capabilities)

	def test_supports_known_capability(self) -> None:
		record = ProviderRecord(**self._valid_kwargs())
		self.assertTrue(record.supports("text"))
		self.assertFalse(record.supports("audio"))

	def test_inactive_status_is_not_active(self) -> None:
		kwargs = self._valid_kwargs()
		kwargs["status"] = "Inactive"
		record = ProviderRecord(**kwargs)
		self.assertFalse(record.is_active)

	def test_rejects_invalid_provider_key(self) -> None:
		kwargs = self._valid_kwargs()
		kwargs["provider_key"] = "Not Valid"
		with self.assertRaises(ProviderConfigError):
			ProviderRecord(**kwargs)

	def test_rejects_invalid_status(self) -> None:
		kwargs = self._valid_kwargs()
		kwargs["status"] = "Pending"
		with self.assertRaises(ProviderConfigError):
			ProviderRecord(**kwargs)

	def test_rejects_unknown_capability(self) -> None:
		kwargs = self._valid_kwargs()
		kwargs["capabilities"] = ("telepathy",)
		with self.assertRaises(ProviderConfigError):
			ProviderRecord(**kwargs)

	def test_rejects_negative_priority(self) -> None:
		kwargs = self._valid_kwargs()
		kwargs["priority"] = -5
		with self.assertRaises(ProviderConfigError):
			ProviderRecord(**kwargs)


class TestAIProviderAdapterContract(TestCase):
	def test_cannot_instantiate_abstract_class_directly(self) -> None:
		with self.assertRaises(TypeError):
			AIProviderAdapter()  # type: ignore[abstract]

	def test_conforming_subclass_can_be_instantiated_and_invoked(self) -> None:
		class FakeAdapter(AIProviderAdapter):
			provider_key = "fake"
			capabilities = ("text",)

			def invoke(self, request: ProviderRequest) -> ProviderResponse:
				return ProviderResponse(
					provider_key=self.provider_key,
					capability=request.capability,
					data={"echo": request.payload},
				)

		adapter = FakeAdapter()
		response = adapter.invoke(
			ProviderRequest(capability="text", payload={"prompt": "hola"}, correlation_id="corr-1")
		)
		self.assertEqual("fake", response.provider_key)
		self.assertEqual({"echo": {"prompt": "hola"}}, response.data)

	def test_incomplete_subclass_cannot_be_instantiated(self) -> None:
		class IncompleteAdapter(AIProviderAdapter):
			provider_key = "incomplete"
			capabilities = ("text",)

		with self.assertRaises(TypeError):
			IncompleteAdapter()  # type: ignore[abstract]
