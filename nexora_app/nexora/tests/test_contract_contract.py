from __future__ import annotations

import ast
import json
import pathlib
import unittest

APP_ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKAGE = APP_ROOT / "nexora"
DOCTYPE_ROOT = PACKAGE / "nexora/doctype"

CONTRACT_DOCTYPES = {
	"NXR Contractor Profile",
	"NXR Contract",
	"NXR Contract Line",
	"NXR Contract Evidence",
	"NXR Contract Amendment",
	"NXR Contract Estimate",
	"NXR Contract Estimate Line",
	"NXR Contract Transaction",
}


class TestContractContract(unittest.TestCase):
	def _definition(self, folder: str) -> dict[str, object]:
		return json.loads((DOCTYPE_ROOT / folder / f"{folder}.json").read_text(encoding="utf-8"))

	def test_doctypes_are_real_and_reuse_entity_finance_and_evidence(self) -> None:
		names = set()
		for folder in (
			"nxr_contractor_profile",
			"nxr_contract",
			"nxr_contract_line",
			"nxr_contract_evidence",
			"nxr_contract_amendment",
			"nxr_contract_estimate",
			"nxr_contract_estimate_line",
			"nxr_contract_transaction",
		):
			definition = self._definition(folder)
			names.add(str(definition["name"]))
			self.assertEqual("NEXORA", definition["module"])
			self.assertTrue((DOCTYPE_ROOT / folder / f"{folder}.py").is_file())
		self.assertEqual(CONTRACT_DOCTYPES, names)
		contract = self._definition("nxr_contract")
		fields = {field["fieldname"]: field for field in contract["fields"]}
		self.assertEqual("NXR Entity", fields["contractor"]["options"])
		self.assertEqual("NXR Contractor Profile", fields["contractor_profile"]["options"])
		self.assertEqual("Project", fields["project"]["options"])
		self.assertEqual("Cost Center", fields["cost_center"]["options"])
		self.assertEqual("NXR Fund Source", fields["fund_source"]["options"])
		self.assertEqual("NXR Contract Line", fields["lines"]["options"])
		self.assertEqual("NXR Contract Evidence", fields["evidence_rows"]["options"])
		self.assertTrue(fields["executed_amount"]["read_only"])
		self.assertTrue(fields["pending_amount"]["read_only"])

	def test_service_exposes_transactional_contract_lifecycle(self) -> None:
		service_path = PACKAGE / "contracts/service.py"
		tree = ast.parse(service_path.read_text(encoding="utf-8"))
		functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
		required = {
			"create_contractor_profile",
			"transition_contractor_profile",
			"create_contract",
			"transition_contract",
			"create_contract_amendment",
			"transition_contract_amendment",
			"create_contract_estimate",
			"transition_contract_estimate",
			"disburse_contract_advance",
			"execute_contract_estimate_payment",
			"return_contract_retention",
			"correct_contract_transaction",
			"get_contract",
			"list_contracts",
		}
		self.assertTrue(required.issubset(functions))
		text = service_path.read_text(encoding="utf-8")
		for token in (
			"start_idempotency",
			"issue_document_number",
			"audit(",
			"service_write",
			".for_update()",
			"execute_central_operation",
			"_resolve_chain",
			"NXR Evidence",
			"NXR Entity",
			"correct_contract_transaction",
			"REAL_RETURN",
			"DOCUMENT_SUBSTITUTION",
		):
			self.assertIn(token, text)
		self.assertNotIn('NXR Contractor"', text)

	def test_controllers_enforce_service_only_immutability(self) -> None:
		for folder in (
			"nxr_contractor_profile",
			"nxr_contract",
			"nxr_contract_amendment",
			"nxr_contract_estimate",
			"nxr_contract_transaction",
		):
			text = (DOCTYPE_ROOT / folder / f"{folder}.py").read_text(encoding="utf-8")
			self.assertIn("require_service_write", text)
			self.assertIn("on_trash", text)
		contract = (DOCTYPE_ROOT / "nxr_contract/nxr_contract.py").read_text(encoding="utf-8")
		self.assertIn("use una adenda", contract)
		self.assertIn("saldo anticipado", contract)
		self.assertIn("saldo retenido", contract)

	def test_permissions_page_workspace_and_hooks_are_connected(self) -> None:
		permissions = (PACKAGE / "permissions.py").read_text(encoding="utf-8")
		for action in ("read_contracts", "create_contract", "manage_contract", "execute_contract"):
			self.assertIn(f'"{action}"', permissions)
		hooks = (PACKAGE / "hooks.py").read_text(encoding="utf-8")
		self.assertIn("nexora.contracts.api.bootstrap", hooks)
		page = json.loads(
			(PACKAGE / "nexora/page/nexora_contracts/nexora_contracts.json").read_text(encoding="utf-8")
		)
		self.assertEqual("nexora-contracts", page["name"])
		script = (PACKAGE / "nexora/page/nexora_contracts/nexora_contracts.js").read_text(encoding="utf-8")
		self.assertIn("nexora.contracts.service.create_contract", script)
		self.assertIn("nexora.contracts.service.transition_contract", script)
		self.assertIn("NEXORA%20Contract", script)
		print_format = json.loads(
			(PACKAGE / "nexora/print_format/nexora_contract/nexora_contract.json").read_text(encoding="utf-8")
		)
		self.assertEqual("NXR Contract", print_format["doc_type"])
		self.assertEqual("Jinja", print_format["print_format_type"])
		workspace = json.loads((PACKAGE / "nexora/workspace/nexora/nexora.json").read_text(encoding="utf-8"))
		shortcuts = {(row["label"], row["type"], row["link_to"]) for row in workspace["shortcuts"]}
		self.assertIn(("Gestión contractual", "Page", "nexora-contracts"), shortcuts)
		self.assertIn(("Contratos", "DocType", "NXR Contract"), shortcuts)

	def test_workflow_executes_contract_runtime_and_concurrency(self) -> None:
		workflow = (APP_ROOT.parent / ".github/workflows/nexora-financial.yml").read_text(encoding="utf-8")
		self.assertIn("test_contract_integration", workflow)
		self.assertIn("contract_concurrency_probe.run", workflow)
		self.assertIn("nexora_contracts.js", workflow)


if __name__ == "__main__":
	unittest.main()
