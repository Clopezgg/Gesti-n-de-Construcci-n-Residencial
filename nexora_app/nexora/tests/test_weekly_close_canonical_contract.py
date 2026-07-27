from __future__ import annotations

import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestWeeklyCloseCanonicalContract(unittest.TestCase):
	def test_public_weekly_endpoints_use_the_canonical_adapter(self) -> None:
		hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
		for method in (
			"calculate_weekly_close",
			"save_weekly_close",
			"correct_weekly_close",
			"list_weekly_closes",
		):
			self.assertIn(f'"nexora.close.service.{method}"', hooks)
			self.assertIn(f'"nexora.close.canonical_weekly.{method}"', hooks)

	def test_internal_service_is_the_single_v3_engine(self) -> None:
		service = (APP_ROOT / "close/service.py").read_text(encoding="utf-8")
		self.assertIn("from nexora.dashboard.snapshot_query import get_executive_snapshot", service)
		self.assertNotIn("from nexora.dashboard.executive import get_executive_snapshot", service)
		self.assertIn('WEEKLY_ENGINE_VERSION = "nexora-analytics-v3"', service)
		self.assertIn("def _stable_close_hash", service)
		self.assertIn('stable_payload.pop("generated_at", None)', service)
		self.assertIn('"snapshot_hash": _stable_close_hash(compact)', service)
		self.assertIn('budget_totals = dict(snapshot.get("budgets", {}))', service)
		self.assertNotIn("budget_totals_as_of", service)

	def test_adapter_only_delegates_without_patching_a_second_engine(self) -> None:
		code = (APP_ROOT / "close/canonical_weekly.py").read_text(encoding="utf-8")
		self.assertIn("from nexora.close import service as weekly_service", code)
		self.assertIn("CANONICAL_WEEKLY_ENGINE_VERSION = weekly_service.WEEKLY_ENGINE_VERSION", code)
		self.assertIn("return weekly_service.save_weekly_close(payload)", code)
		self.assertNotIn("get_executive_snapshot", code)
		self.assertNotIn("stable_payload_hash", code)
		self.assertNotIn("frappe.get_doc", code)
		self.assertNotIn("NXR Operation Effect", code)

	def test_snapshot_hash_excludes_only_the_volatile_generation_timestamp(self) -> None:
		code = (APP_ROOT / "close/service.py").read_text(encoding="utf-8")
		self.assertIn("def _stable_close_hash", code)
		self.assertIn('stable_payload.pop("generated_at", None)', code)
		self.assertIn("return canonical_snapshot_hash(stable_payload)", code)
		self.assertNotIn('stable_payload.pop("totals"', code)
		self.assertNotIn('stable_payload.pop("project"', code)
		self.assertNotIn('stable_payload.pop("period"', code)

	def test_closing_ui_requires_project_and_preserves_historical_context(self) -> None:
		code = (APP_ROOT / "nexora/page/nexora-closing/nexora-closing.js").read_text(encoding="utf-8")
		for marker in (
			"requiresProjectSelection()",
			"historyRows = new Map",
			"row.week_start",
			"row.week_end",
			"row.project || null",
			"calculationChanged()",
			"catch (error)",
			'frappe.route_options = null',
			'data-state="loading"',
		):
			self.assertIn(marker, code)
		self.assertNotIn("correct($(this).data", code)

	def test_correction_is_compensatory_and_never_deletes_the_original(self) -> None:
		page = (APP_ROOT / "nexora/page/nexora-closing/nexora-closing.js").read_text(encoding="utf-8")
		controller = (
			APP_ROOT / "nexora/doctype/nxr_weekly_close/nxr_weekly_close.py"
		).read_text(encoding="utf-8")
		self.assertIn("Corrección registrada sin sobrescribir el cierre original", page)
		self.assertIn("def on_trash", controller)
		self.assertIn("no se elimina", controller.lower())


if __name__ == "__main__":
	unittest.main()
