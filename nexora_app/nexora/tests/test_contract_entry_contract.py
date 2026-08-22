from __future__ import annotations

import pathlib
import unittest

APP = pathlib.Path(__file__).resolve().parents[2]
SERVICE = APP / "nexora/contracts/service.py"
PAGE = APP / "nexora/nexora/page/nexora_contracts/nexora_contracts.js"


class TestGuidedContractEntry(unittest.TestCase):
	def test_guided_backend_reuses_canonical_contract_services(self) -> None:
		text = SERVICE.read_text(encoding="utf-8")
		self.assertIn("def create_contract_bundle(", text)
		fn = text.split("def create_contract_bundle(", 1)[1].split("\n\n@frappe.whitelist", 1)[0]
		self.assertIn("create_contractor_profile(", fn)
		self.assertIn("transition_contractor_profile(", fn)
		self.assertIn("create_contract(contract_payload)", fn)
		self.assertNotIn('"doctype": "NXR Contract"', fn)

	def test_guided_ui_collects_project_cost_value_time_and_contractor(self) -> None:
		text = PAGE.read_text(encoding="utf-8")
		self.assertIn("Nueva contratación", text)
		fn = text.split("async function createContractBundle()", 1)[1].split("\n\tasync function createContract()", 1)[0]
		for field in ("contractor", "project", "cost_center", "labor_amount", "material_amount", "start_date", "end_date", "scope"):
			with self.subTest(field=field):
				self.assertIn(f'fieldname: "{field}"', fn)
		self.assertIn("create_contract_bundle", fn)

	def test_contracts_allow_central_source_without_making_project_the_fund_owner(self) -> None:
		text = SERVICE.read_text(encoding="utf-8")
		segment = text.split("def create_contract(", 1)[1].split("\n\ndef transition_contract", 1)[0]
		self.assertIn("not in {None, project}", segment)


if __name__ == "__main__":
	unittest.main()
