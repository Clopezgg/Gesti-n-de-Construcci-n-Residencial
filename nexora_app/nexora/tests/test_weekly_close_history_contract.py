from __future__ import annotations

import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestWeeklyCloseHistoryContract(unittest.TestCase):
	def test_weekly_close_uses_the_single_versioned_historical_engine(self) -> None:
		code = (APP_ROOT / "close/service.py").read_text(encoding="utf-8")
		for marker in (
			"from nexora.dashboard.snapshot_query import get_executive_snapshot",
			'WEEKLY_ENGINE_VERSION = "nexora-analytics-v3"',
			'closing_reserved = source_totals.get("closing_reserved_hnl", 0)',
			'"pending_hnl": closing_reserved',
			'"committed_hnl": closing_reserved',
			'budget_totals = dict(snapshot.get("budgets", {}))',
			'budget_totals.pop("lines", None)',
			'"snapshot_basis"',
			"no usa el estado mutable actual",
			'"snapshot_hash": _stable_close_hash(compact)',
		):
			self.assertIn(marker, code)
		self.assertNotIn("budget_totals_as_of", code)
		self.assertNotIn(
			'snapshot.get("pending_accounts", {}).get("total_hnl", 0)',
			code,
		)

	def test_budget_cutoff_selects_latest_effective_version(self) -> None:
		code = (APP_ROOT / "close/as_of.py").read_text(encoding="utf-8")
		for marker in (
			"newer.effective_date<=%(period_end)s",
			"newer.effective_date>b.effective_date",
			"newer.version>b.version",
			"b.effective_date<=%(period_end)s",
			"newer.name IS NULL",
			"FROM `tabNXR Budget Line`",
			"o.operation_date<=%(period_end)s",
			"FROM `tabNXR Operation Effect` e",
			'"total_available_hnl": number(approved - used)',
		):
			self.assertIn(marker, code)

	def test_snapshot_discloses_non_historical_contract_and_reconciliation_basis(self) -> None:
		code = (APP_ROOT / "close/service.py").read_text(encoding="utf-8")
		self.assertIn("la versión histórica ", code)
		self.assertIn("contractual requiere su propio historial", code)
		self.assertIn("Estado documental vigente al momento de generar el cierre", code)
		self.assertIn("La huella excluye únicamente generated_at", code)


if __name__ == "__main__":
	unittest.main()
