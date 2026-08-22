from __future__ import annotations

import json
import pathlib
import unittest

APP = pathlib.Path(__file__).resolve().parents[2]
ACCOUNT_JSON = APP / "nexora/nexora/doctype/nxr_financial_account/nxr_financial_account.json"
ACCOUNT_CONTROLLER = APP / "nexora/nexora/doctype/nxr_financial_account/nxr_financial_account.py"
TREASURY_SERVICE = APP / "nexora/financial/central_treasury.py"
TREASURY_PATCH = APP / "nexora/patches/v0_1/ensure_central_remittance_account.py"
PATCHES = APP / "nexora/patches.txt"


class TestCentralTreasuryContract(unittest.TestCase):
	def test_financial_account_exposes_unique_system_identity(self) -> None:
		payload = json.loads(ACCOUNT_JSON.read_text(encoding="utf-8"))
		fields = {row["fieldname"]: row for row in payload["fields"]}
		self.assertEqual("Counterparty\nTreasury", fields["account_role"]["options"])
		self.assertEqual(1, fields["technical_key"]["unique"])
		self.assertEqual(1, fields["technical_key"]["read_only"])
		self.assertEqual(1, fields["system_managed"]["read_only"])

	def test_central_treasury_service_and_patch_are_registered(self) -> None:
		self.assertTrue(TREASURY_SERVICE.is_file())
		self.assertTrue(TREASURY_PATCH.is_file())
		lines = [line.strip() for line in PATCHES.read_text(encoding="utf-8").splitlines()]
		self.assertEqual(1, lines.count("nexora.patches.v0_1.ensure_central_remittance_account"))

	def test_system_managed_accounts_are_immutable_and_not_deletable(self) -> None:
		controller = ACCOUNT_CONTROLLER.read_text(encoding="utf-8")
		self.assertIn("SYSTEM_MANAGED_FIELDS", controller)
		self.assertIn("def on_trash", controller)
		self.assertIn("system_managed", controller)


if __name__ == "__main__":
	unittest.main()
