from __future__ import annotations

from unittest import TestCase

from nexora.intelligence.prompt_optimizer import (
	CHARS_PER_TOKEN_ESTIMATE,
	estimate_tokens,
	normalize_whitespace,
	optimize_prompt,
	truncate_to_budget,
)


class TestEstimateTokens(TestCase):
	def test_uses_the_documented_ratio(self) -> None:
		text = "x" * (CHARS_PER_TOKEN_ESTIMATE * 10)
		self.assertEqual(10, estimate_tokens(text))

	def test_empty_string_is_zero(self) -> None:
		self.assertEqual(0, estimate_tokens(""))

	def test_never_negative(self) -> None:
		self.assertGreaterEqual(estimate_tokens("a"), 0)


class TestNormalizeWhitespace(TestCase):
	def test_collapses_repeated_spaces(self) -> None:
		self.assertEqual("hola mundo", normalize_whitespace("hola     mundo"))

	def test_collapses_repeated_tabs(self) -> None:
		self.assertEqual("hola mundo", normalize_whitespace("hola\t\t\tmundo"))

	def test_collapses_excess_blank_lines(self) -> None:
		self.assertEqual("hola\n\nmundo", normalize_whitespace("hola\n\n\n\n\nmundo"))

	def test_preserves_a_single_blank_line(self) -> None:
		self.assertEqual("hola\n\nmundo", normalize_whitespace("hola\n\nmundo"))

	def test_strips_leading_and_trailing_whitespace(self) -> None:
		self.assertEqual("hola", normalize_whitespace("   hola   "))

	def test_never_changes_a_word(self) -> None:
		self.assertEqual("El gasto fue de HNL 500.00", normalize_whitespace("El   gasto  fue de HNL 500.00"))

	def test_does_not_collapse_newlines_into_spaces(self) -> None:
		# Un salto de línea simple es contenido significativo (párrafos,
		# listas); solo se colapsan espacios/tabs horizontales.
		self.assertEqual("uno\ndos", normalize_whitespace("uno\ndos"))


class TestTruncateToBudget(TestCase):
	def test_returns_unchanged_when_within_budget(self) -> None:
		text = "hola mundo"
		self.assertEqual(text, truncate_to_budget(text, max_chars=100))

	def test_returns_unchanged_at_exactly_the_budget(self) -> None:
		text = "x" * 50
		self.assertEqual(text, truncate_to_budget(text, max_chars=50))

	def test_truncates_and_keeps_head_and_tail(self) -> None:
		text = "HEAD" + ("x" * 1000) + "TAIL"
		result = truncate_to_budget(text, max_chars=100)
		self.assertTrue(result.startswith("HEAD"))
		self.assertTrue(result.endswith("TAIL"))
		self.assertIn("recortado", result)

	def test_result_never_exceeds_the_budget(self) -> None:
		text = "y" * 10_000
		result = truncate_to_budget(text, max_chars=500)
		self.assertLessEqual(len(result), 500)

	def test_result_never_exceeds_the_budget_even_when_smaller_than_the_marker(self) -> None:
		text = "z" * 10_000
		result = truncate_to_budget(text, max_chars=10)
		self.assertLessEqual(len(result), 10)

	def test_zero_budget_returns_empty_string(self) -> None:
		self.assertEqual("", truncate_to_budget("algo", max_chars=0))


class TestOptimizePrompt(TestCase):
	def test_reports_no_truncation_for_a_short_prompt(self) -> None:
		result = optimize_prompt("hola   mundo", max_chars=1000)
		self.assertFalse(result["was_truncated"])
		self.assertEqual("hola mundo", result["text"])

	def test_reports_truncation_for_a_long_prompt(self) -> None:
		result = optimize_prompt("x" * 100_000, max_chars=100)
		self.assertTrue(result["was_truncated"])
		self.assertLessEqual(result["final_chars"], 100)

	def test_original_chars_reflects_the_input_before_normalization(self) -> None:
		result = optimize_prompt("a   b", max_chars=1000)
		self.assertEqual(5, result["original_chars"])
		self.assertEqual(3, result["final_chars"])

	def test_estimated_tokens_matches_the_final_text(self) -> None:
		result = optimize_prompt("x" * 40, max_chars=1000)
		self.assertEqual(estimate_tokens(result["text"]), result["estimated_tokens"])

	def test_never_raises_on_empty_input(self) -> None:
		result = optimize_prompt("", max_chars=1000)
		self.assertEqual("", result["text"])
		self.assertFalse(result["was_truncated"])
