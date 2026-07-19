from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[3] / "scripts" / "validate_commit_titles.py"
SPEC = importlib.util.spec_from_file_location("validate_commit_titles", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
	raise RuntimeError(f"Unable to load {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CommitTitleValidationTest(unittest.TestCase):
	def test_accepts_conventional_titles(self) -> None:
		self.assertTrue(MODULE.is_valid_title("fix(finance): reconcile approved expenses"))
		self.assertTrue(MODULE.is_valid_title("docs: explain safe deployment"))

	def test_accepts_controlled_block_titles(self) -> None:
		self.assertTrue(MODULE.is_valid_title("[B01] Audit architecture and branch differences"))
		self.assertTrue(MODULE.is_valid_title("[B12] Validate deployment and final regression"))

	def test_rejects_generic_or_invalid_titles(self) -> None:
		for title in ("fix", "changes", "[B00] Invalid block", "[B13] Invalid block", "[B01]   "):
			with self.subTest(title=title):
				self.assertFalse(MODULE.is_valid_title(title))


if __name__ == "__main__":
	unittest.main()
