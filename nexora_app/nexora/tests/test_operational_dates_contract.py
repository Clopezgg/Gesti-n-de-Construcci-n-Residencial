from __future__ import annotations

import unittest
from datetime import date, datetime

from nexora.financial.operational_dates import OperationalDateError, month_key


class TestOperationalDateContract(unittest.TestCase):
	def test_month_key_accepts_dates_and_iso_text(self) -> None:
		self.assertEqual("2026-07", month_key(date(2026, 7, 28)))
		self.assertEqual("2026-07", month_key(datetime(2026, 7, 28, 13, 45)))
		self.assertEqual("2026-07", month_key("2026-07-28"))
		self.assertEqual("2026-07", month_key("2026-07-28 13:45:00"))

	def test_month_key_rejects_invalid_text_with_domain_error(self) -> None:
		with self.assertRaisesRegex(OperationalDateError, "no es válida"):
			month_key("28/07/2026")


if __name__ == "__main__":
	unittest.main()
