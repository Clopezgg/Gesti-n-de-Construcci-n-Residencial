from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "quality_migration.py"
SPEC = importlib.util.spec_from_file_location("cc_quality_migration", MODULE)
QUALITY_MIGRATION = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(QUALITY_MIGRATION)


class QualityMigrationContractTest(unittest.TestCase):
	def test_active_historical_progress_becomes_approved_without_changing_percent(self):
		self.assertEqual(
			QUALITY_MIGRATION.normalize_legacy_progress("active", "good"),
			("approved", "passed"),
		)

	def test_cancelled_or_failed_history_remains_non_active(self):
		self.assertEqual(
			QUALITY_MIGRATION.normalize_legacy_progress("cancelled", "poor"),
			("cancelled", "failed"),
		)

	def test_unknown_quality_remains_pending_instead_of_being_invented(self):
		self.assertEqual(
			QUALITY_MIGRATION.normalize_legacy_progress("verified", "legacy_unknown"),
			("approved", "pending"),
		)


if __name__ == "__main__":
	unittest.main()
