from __future__ import annotations

import unittest

from nexora.dashboard.analytics_core import net_received_amount


class TestDashboardNetIncome(unittest.TestCase):
	def test_net_income_subtracts_cancelled_received_effects(self) -> None:
		self.assertEqual(100_000, net_received_amount(180_000, 80_000))

	def test_period_can_report_negative_net_income_when_cancellation_is_later(self) -> None:
		self.assertEqual(-80_000, net_received_amount(0, 80_000))

	def test_unrelated_reversals_are_not_passed_as_income_reversals(self) -> None:
		general_reversed_hnl = 80_000
		reversed_inflow_hnl = 0
		self.assertNotEqual(general_reversed_hnl, reversed_inflow_hnl)
		self.assertEqual(180_000, net_received_amount(180_000, reversed_inflow_hnl))


if __name__ == "__main__":
	unittest.main()
