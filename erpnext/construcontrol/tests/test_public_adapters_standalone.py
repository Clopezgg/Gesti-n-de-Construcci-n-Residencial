from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WEEKLY = ROOT / "erpnext" / "construcontrol" / "weekly.py"
EXECUTIVE = ROOT / "erpnext" / "construcontrol" / "executive.py"
CLOSING_PAGE = (
	ROOT
	/ "erpnext"
	/ "construcontrol"
	/ "page"
	/ "construcontrol_closing_center"
	/ "construcontrol_closing_center.js"
)
DASHBOARD = (
	ROOT / "erpnext" / "construcontrol" / "page" / "construcontrol_dashboard" / "construcontrol_dashboard.js"
)


class PublicAdaptersTest(unittest.TestCase):
	def test_closing_adapter_is_explicit_and_bound_to_persisted_routes(self) -> None:
		service = WEEKLY.read_text(encoding="utf-8")
		page = CLOSING_PAGE.read_text(encoding="utf-8")
		self.assertIn("WEEKLY_ADAPTER_REMOVAL_CONDITION", service)
		for method in ("preview_weekly_closing", "create_weekly_closing", "reopen_weekly_closing"):
			self.assertIn(f"{method} = _implementation.{method}", service)
		self.assertIn("erpnext.construcontrol.weekly.preview_weekly_closing", page)
		self.assertNotIn("def __getattr__", service)

	def test_dashboard_adapter_is_explicit_and_bound_to_persisted_route(self) -> None:
		service = EXECUTIVE.read_text(encoding="utf-8")
		page = DASHBOARD.read_text(encoding="utf-8")
		self.assertIn("EXECUTIVE_ADAPTER_REMOVAL_CONDITION", service)
		self.assertIn("def get_executive_dashboard", service)
		self.assertIn("erpnext.construcontrol.executive.get_executive_dashboard", page)
		self.assertNotIn("def __getattr__", service)


if __name__ == "__main__":
	unittest.main()
