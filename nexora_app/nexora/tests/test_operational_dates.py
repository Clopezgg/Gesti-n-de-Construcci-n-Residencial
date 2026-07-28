from __future__ import annotations

import unittest
from datetime import date

from nexora.financial.operational_dates import (
	OperationalDateError,
	month_key,
	parse_document_date,
	validate_document_date,
)


class TestOperationalDates(unittest.TestCase):
	def test_historical_document_date_is_preserved(self) -> None:
		value = validate_document_date("2026-05-27", today=date(2026, 7, 27))
		self.assertEqual(date(2026, 5, 27), value)
		self.assertEqual("2026-05", month_key(value))

	def test_missing_date_uses_only_explicit_fallback(self) -> None:
		self.assertEqual(
			date(2026, 7, 27),
			parse_document_date("", fallback=date(2026, 7, 27)),
		)
		with self.assertRaisesRegex(OperationalDateError, "obligatoria"):
			parse_document_date("")

	def test_future_date_is_rejected(self) -> None:
		with self.assertRaisesRegex(OperationalDateError, "futuro"):
			validate_document_date("2026-07-28", today=date(2026, 7, 27))

	def test_correction_cannot_precede_original_document(self) -> None:
		with self.assertRaisesRegex(OperationalDateError, "anterior"):
			validate_document_date(
				"2026-05-26",
				today=date(2026, 7, 27),
				reference_date="2026-05-27",
			)


if __name__ == "__main__":
	unittest.main()
