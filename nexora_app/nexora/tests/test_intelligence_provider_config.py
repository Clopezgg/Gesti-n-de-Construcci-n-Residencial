from __future__ import annotations

from unittest import TestCase

from nexora.intelligence.core import (
	COST_HINTS,
	VALIDATION_STATES,
	ProviderConfigError,
	validate_cost_hint,
	validate_default_model,
	validate_max_tokens,
	validate_temperature,
	validate_timeout_seconds,
	validate_validation_state,
)


class TestConstants(TestCase):
	def test_cost_hints_are_correct(self) -> None:
		self.assertEqual({"Low", "Medium", "High"}, set(COST_HINTS))

	def test_validation_states_are_correct(self) -> None:
		self.assertEqual({"Not Configured", "Format Valid", "Format Invalid"}, set(VALIDATION_STATES))


class TestValidateDefaultModel(TestCase):
	def test_accepts_a_model_name(self) -> None:
		self.assertEqual("gpt-4o-mini", validate_default_model("gpt-4o-mini"))

	def test_trims_whitespace(self) -> None:
		self.assertEqual("gpt-4o-mini", validate_default_model("  gpt-4o-mini  "))

	def test_none_is_valid_and_means_unset(self) -> None:
		self.assertIsNone(validate_default_model(None))

	def test_empty_string_is_valid_and_means_unset(self) -> None:
		self.assertIsNone(validate_default_model(""))

	def test_whitespace_only_is_valid_and_means_unset(self) -> None:
		self.assertIsNone(validate_default_model("   "))

	def test_rejects_too_long(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_default_model("x" * 141)

	def test_accepts_exactly_the_maximum_length(self) -> None:
		value = "x" * 140
		self.assertEqual(value, validate_default_model(value))


class TestValidateTimeoutSeconds(TestCase):
	def test_accepts_within_bounds(self) -> None:
		self.assertEqual(30, validate_timeout_seconds(30))

	def test_accepts_numeric_string(self) -> None:
		self.assertEqual(45, validate_timeout_seconds("45"))

	def test_accepts_lower_bound(self) -> None:
		self.assertEqual(1, validate_timeout_seconds(1))

	def test_accepts_upper_bound(self) -> None:
		self.assertEqual(600, validate_timeout_seconds(600))

	def test_rejects_zero(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_timeout_seconds(0)

	def test_rejects_above_upper_bound(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_timeout_seconds(601)

	def test_rejects_negative(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_timeout_seconds(-5)

	def test_rejects_non_numeric(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_timeout_seconds("slow")


class TestValidateTemperature(TestCase):
	def test_accepts_within_bounds(self) -> None:
		self.assertEqual(0.7, validate_temperature(0.7))

	def test_accepts_lower_bound(self) -> None:
		self.assertEqual(0.0, validate_temperature(0.0))

	def test_accepts_upper_bound(self) -> None:
		self.assertEqual(2.0, validate_temperature(2.0))

	def test_accepts_numeric_string(self) -> None:
		self.assertEqual(0.5, validate_temperature("0.5"))

	def test_rejects_below_lower_bound(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_temperature(-0.1)

	def test_rejects_above_upper_bound(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_temperature(2.1)

	def test_rejects_non_numeric(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_temperature("hot")


class TestValidateMaxTokens(TestCase):
	def test_accepts_within_bounds(self) -> None:
		self.assertEqual(1024, validate_max_tokens(1024))

	def test_accepts_lower_bound(self) -> None:
		self.assertEqual(1, validate_max_tokens(1))

	def test_accepts_upper_bound(self) -> None:
		self.assertEqual(200_000, validate_max_tokens(200_000))

	def test_rejects_zero(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_max_tokens(0)

	def test_rejects_above_upper_bound(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_max_tokens(200_001)

	def test_rejects_non_numeric(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_max_tokens("many")


class TestValidateCostHint(TestCase):
	def test_accepts_each_known_value(self) -> None:
		for value in COST_HINTS:
			self.assertEqual(value, validate_cost_hint(value))

	def test_rejects_unknown_value(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_cost_hint("Cheap")

	def test_rejects_lowercase_variant(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_cost_hint("low")

	def test_rejects_none(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_cost_hint(None)


class TestValidateValidationState(TestCase):
	def test_accepts_each_known_value(self) -> None:
		for value in VALIDATION_STATES:
			self.assertEqual(value, validate_validation_state(value))

	def test_rejects_unknown_value(self) -> None:
		with self.assertRaises(ProviderConfigError):
			validate_validation_state("Confirmed")
