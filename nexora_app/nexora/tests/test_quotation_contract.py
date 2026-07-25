from __future__ import annotations

import ast
import json
import pathlib
import unittest

APP_ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKAGE = APP_ROOT / "nexora"
DOCTYPE_ROOT = PACKAGE / "nexora/doctype"


class TestQuotationContract(unittest.TestCase):
	def test_quotation_doctype_is_defined(self) -> None:
		folder = DOCTYPE_ROOT / "nxr_supplier_quotation"
		definition = json.loads((folder / "nxr_supplier_quotation.json").read_text(encoding="utf-8"))
		self.assertEqual("NXR Supplier Quotation", definition["name"])
		self.assertEqual("NEXORA", definition["module"])
		fields = {field["fieldname"]: field for field in definition["fields"]}
		self.assertEqual("NXR Purchase Request", fields["purchase_request"]["options"])
		self.assertEqual("NXR Supplier Profile", fields["supplier_profile"]["options"])
		self.assertEqual("NXR Entity", fields["supplier_entity"]["options"])
		self.assertEqual("NXR Evidence", fields["evidence"]["options"])
		self.assertTrue(fields["selected"]["read_only"])
		self.assertTrue(fields["document_number"]["read_only"])
		self.assertTrue((folder / "nxr_supplier_quotation.py").is_file())

	def test_quotation_line_doctype_is_defined(self) -> None:
		folder = DOCTYPE_ROOT / "nxr_supplier_quotation_line"
		definition = json.loads((folder / "nxr_supplier_quotation_line.json").read_text(encoding="utf-8"))
		self.assertEqual("NXR Supplier Quotation Line", definition["name"])
		self.assertTrue(definition["istable"])
		fields = {field["fieldname"]: field for field in definition["fields"]}
		self.assertEqual("Item", fields["catalog_item"]["options"])
		self.assertEqual("UOM", fields["uom"]["options"])
		self.assertTrue(fields["amount"]["read_only"])

	def test_quotation_service_exposes_lifecycle(self) -> None:
		service_path = PACKAGE / "purchases/quotation_service.py"
		self.assertTrue(service_path.is_file())
		tree = ast.parse(service_path.read_text(encoding="utf-8"))
		functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
		self.assertTrue(
			{
				"create_quotation",
				"transition_quotation",
				"get_quotation",
				"list_quotations",
				"compare_quotations",
			}.issubset(functions)
		)
		text = service_path.read_text(encoding="utf-8")
		for token in (
			"issue_document_number",
			"start_idempotency",
			"service_write",
			".for_update()",
			"audit(",
			"complete_idempotency",
			"canonical_payload_hash",
		):
			self.assertIn(token, text)

	def test_quotation_controller_enforces_boundary(self) -> None:
		controller = (DOCTYPE_ROOT / "nxr_supplier_quotation/nxr_supplier_quotation.py").read_text(
			encoding="utf-8"
		)
		self.assertIn("require_service_write", controller)
		self.assertIn("on_trash", controller)
		permissions = (PACKAGE / "permissions.py").read_text(encoding="utf-8")
		self.assertIn('"create_purchase_request"', permissions)
		self.assertIn('"read_purchases"', permissions)

	def test_quotation_page_is_connected(self) -> None:
		page_root = PACKAGE / "nexora/page/nexora_quotations"
		self.assertTrue((page_root / "nexora_quotations.json").is_file())
		self.assertTrue((page_root / "nexora_quotations.js").is_file())
		page = json.loads((page_root / "nexora_quotations.json").read_text(encoding="utf-8"))
		self.assertEqual("nexora-quotations", page["name"])
		script = (page_root / "nexora_quotations.js").read_text(encoding="utf-8")
		self.assertIn("nexora.purchases.quotation_service.create_quotation", script)
		self.assertIn("nexora.purchases.quotation_service.transition_quotation", script)
		self.assertIn("nexora.purchases.quotation_service.compare_quotations", script)

	def test_workflow_references_quotation_tests(self) -> None:
		workflow = (APP_ROOT.parent / ".github/workflows/nexora-financial.yml").read_text(encoding="utf-8")
		self.assertIn("test_quotation_core", workflow)
		self.assertIn("test_quotation_integration", workflow)
		self.assertIn("nexora_quotations.js", workflow)
		self.assertIn("test_*contract.py", workflow)


if __name__ == "__main__":
	unittest.main()
