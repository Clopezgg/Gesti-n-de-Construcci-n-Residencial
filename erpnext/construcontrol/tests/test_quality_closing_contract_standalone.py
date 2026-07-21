from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
	path = ROOT / f"{name}.py"
	spec = importlib.util.spec_from_file_location(f"cc_{name}", path)
	module = importlib.util.module_from_spec(spec)
	assert spec and spec.loader
	spec.loader.exec_module(module)
	return module


QUALITY = load("quality")
CLOSING = load("closing")


class QualityClosingContractTest(unittest.TestCase):
	def test_progress_requires_scope_identity_and_valid_percent(self):
		with self.assertRaisesRegex(ValueError, "proyecto, fase, fecha y responsable"):
			QUALITY.validate_progress_contract({"progress_percent": 10})
		with self.assertRaisesRegex(ValueError, "entre 0 y 100"):
			QUALITY.validate_progress_contract(
				{
					"project": "P1",
					"phase": "F1",
					"posting_date": "2026-07-19",
					"responsible": "U1",
					"progress_percent": 101,
				}
			)

	def test_progress_regression_requires_manager_reason(self):
		values = {
			"project": "P1",
			"phase": "F1",
			"posting_date": "2026-07-19",
			"responsible": "U1",
			"progress_percent": 25,
		}
		with self.assertRaisesRegex(ValueError, "reducción del avance"):
			QUALITY.validate_progress_contract(values, previous_percent=40)
		approved = QUALITY.validate_progress_contract(
			{**values, "regression_reason": "Corrección de medición"},
			previous_percent=40,
			manager_override=True,
		)
		self.assertEqual(approved["progress_percent"], 25)

	def test_failed_quality_requires_observation_and_alert(self):
		values = {
			"project": "P1",
			"phase": "F1",
			"posting_date": "2026-07-19",
			"responsible": "U1",
			"progress_percent": 25,
			"quality_status": "failed",
		}
		with self.assertRaisesRegex(ValueError, "falla de calidad"):
			QUALITY.validate_progress_contract(values)
		result = QUALITY.validate_progress_contract(
			{**values, "observations": "Fisura", "alert_level": "critical"}
		)
		self.assertEqual(result["quality_status"], "failed")

	def test_evidence_must_be_private_and_safe(self):
		values = {
			"project": "P1",
			"progress_update": "A1",
			"evidence_file": "/private/files/a.jpg",
			"capture_source": "camera",
		}
		with self.assertRaisesRegex(ValueError, "archivo privado"):
			QUALITY.validate_evidence_contract(
				values,
				file_is_private=False,
				file_size=100,
				mime_type="image/jpeg",
			)
		result = QUALITY.validate_evidence_contract(
			values,
			file_is_private=True,
			file_size=100,
			mime_type="image/jpeg",
		)
		self.assertEqual(result["capture_source"], "camera")

	def test_weekly_snapshot_reconciles_cash_commitment_and_projected_balance(self):
		snapshot = CLOSING.closing_snapshot(
			initial_balance=100,
			income=1000,
			recognized_expense=400,
			paid_expense=250,
			pending_expense=150,
			inventory_movements=3,
			progress_updates=2,
		)
		self.assertEqual(snapshot["final_balance_hnl"], 850)
		self.assertEqual(snapshot["projected_balance_hnl"], 700)
		self.assertEqual(snapshot["reconciliation_status"], "pending")

	def test_weekly_repeat_is_idempotent_and_closed_change_requires_reopen(self):
		snapshot = CLOSING.closing_snapshot(
			initial_balance=0,
			income=1000,
			recognized_expense=250,
			paid_expense=250,
			pending_expense=0,
		)
		digest = CLOSING.snapshot_digest(snapshot)
		self.assertEqual(CLOSING.resolve_repeat("closed", digest, digest), "reuse")
		self.assertEqual(CLOSING.resolve_repeat("draft", "old", digest), "refresh")
		self.assertEqual(CLOSING.resolve_repeat("closed", "old", digest), "reopen_required")


if __name__ == "__main__":
	unittest.main()
