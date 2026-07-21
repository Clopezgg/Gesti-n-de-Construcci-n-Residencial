from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[3] / "scripts" / "validate_commit_titles.py"
SPEC = importlib.util.spec_from_file_location("validate_commit_titles", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
	raise RuntimeError(f"Unable to load {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CommitTitleValidationTest(unittest.TestCase):
	def test_registers_only_the_exact_immutable_exception(self) -> None:
		self.assertEqual(
			MODULE.IMMUTABLE_TITLE_EXCEPTIONS,
			{"01d5684d3449e22669c81fdc91539dd64278f86b": "noop"},
		)
		self.assertTrue(MODULE.is_valid_commit("01d5684d3449e22669c81fdc91539dd64278f86b", "noop"))
		self.assertFalse(MODULE.is_valid_commit("01d5684d3449e22669c81fdc91539dd64278f86b", "noop changed"))
		self.assertFalse(MODULE.is_valid_commit("0" * 40, "noop"))

	def test_accepts_conventional_titles(self) -> None:
		self.assertTrue(MODULE.is_valid_title("fix(finance): reconcile approved expenses"))
		self.assertTrue(MODULE.is_valid_title("docs: explain safe deployment"))

	def test_accepts_controlled_block_and_certification_titles(self) -> None:
		self.assertTrue(MODULE.is_valid_title("[B01] Audit architecture and branch differences"))
		self.assertTrue(MODULE.is_valid_title("[B12] Validate deployment and final regression"))
		self.assertTrue(MODULE.is_valid_title("[CERT] Record verified runtime receipt"))

	def test_grandfathers_history_before_policy_checkpoint(self) -> None:
		with patch.object(
			MODULE.subprocess,
			"run",
			return_value=SimpleNamespace(returncode=0),
		):
			self.assertEqual(
				MODULE.validation_range("base", "head"),
				f"{MODULE.POLICY_ENFORCEMENT_SHA}..head",
			)

	def test_falls_back_to_pr_base_when_checkpoint_is_unavailable(self) -> None:
		with patch.object(
			MODULE.subprocess,
			"run",
			return_value=SimpleNamespace(returncode=1),
		):
			self.assertEqual(MODULE.validation_range("base", "head"), "base..head")

	def test_rejects_generic_legacy_or_invalid_titles(self) -> None:
		for title in (
			"fix",
			"changes",
			"Update code",
			"Work in progress",
			"Record ConstruControl runtime verification receipt [skip ci]",
			"[B00] Invalid block",
			"[B13] Invalid block",
			"[B01]   ",
		):
			with self.subTest(title=title):
				self.assertFalse(MODULE.is_valid_title(title))

	def test_reports_sha_and_title_for_every_invalid_commit(self) -> None:
		commits = [
			("a" * 40, "fix(core): valid"),
			("b" * 40, "noop"),
			("01d5684d3449e22669c81fdc91539dd64278f86b", "noop"),
		]
		self.assertEqual(MODULE.invalid_commits(commits), [("b" * 40, "noop")])


if __name__ == "__main__":
	unittest.main()
