from __future__ import annotations

import pathlib
import unittest

import nexora

REPO_ROOT = pathlib.Path(nexora.__file__).resolve().parents[2]


class TestBrowserAcceptanceContract(unittest.TestCase):
	def test_browser_suite_covers_executive_surfaces(self) -> None:
		code = (REPO_ROOT / "scripts/nexora_browser_smoke.mjs").read_text(encoding="utf-8")
		for marker in (
			'"nexora-dashboard"',
			'"nexora-reports"',
			'"nexora-closing"',
			'"desktop-chromium"',
			'"iphone-13-webkit"',
			"validateDashboard",
			"validateReports",
			"validateClosing",
			"validatePwa",
			"validateResponsiveLayout",
			"bounded_operational_queries",
			"nexora-analytics-v3",
		):
			self.assertIn(marker, code)

	def test_quick_actions_use_the_current_single_handler_contract(self) -> None:
		code = (REPO_ROOT / "scripts/nexora_browser_smoke.mjs").read_text(encoding="utf-8")
		self.assertIn('[data-action="expense"]', code)
		self.assertIn('[data-action="income"]', code)
		self.assertNotIn('[data-route="nexora-finance"][data-action="expense"]', code)
		self.assertNotIn('[data-route="nexora-finance"][data-action="income"]', code)

	def test_browser_suite_calculates_but_does_not_persist_a_weekly_close(self) -> None:
		code = (REPO_ROOT / "scripts/nexora_browser_smoke.mjs").read_text(encoding="utf-8")
		self.assertIn(".nxr-calculate", code)
		self.assertNotIn("save_weekly_close", code)
		self.assertNotIn("correct_weekly_close", code)


if __name__ == "__main__":
	unittest.main()
