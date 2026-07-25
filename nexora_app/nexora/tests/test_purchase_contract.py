from __future__ import annotations

import ast
import json
import pathlib
import unittest

APP_ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKAGE = APP_ROOT / "nexora"
DOCTYPE_ROOT = PACKAGE / "nexora/doctype"


class TestPurchaseContract(unittest.TestCase):
	def test_supplier_profile_reuses_canonical_directory_and_compliance(self) -> None:
		folder = DOCTYPE_ROOT / "nxr_supplier_profile"
		definition = json.loads((folder / "nxr_supplier_profile.json").read_text(encoding="utf-8"))
		self.assertEqual("NXR Supplier Profile", definition["name"])
		self.assertEqual("NEXORA", definition["module"])
		fields = {field["fieldname"]: field for field in definition["fields"]}
		self.assertEqual("NXR Entity", fields["entity"]["options"])
		self.assertEqual("NXR Entity Role", fields["entity_role"]["options"])
		self.assertEqual("NXR Entity Compliance", fields["compliance"]["options"])
		self.assertEqual("NXR Evidence", fields["evidence"]["options"])
		self.assertTrue(fields["compliance_status"]["read_only"])
		self.assertTrue((folder / "nxr_supplier_profile.py").is_file())

	def test_supplier_service_exposes_controlled_lifecycle(self) -> None:
		service_path = PACKAGE / "purchases/service.py"
		tree = ast.parse(service_path.read_text(encoding="utf-8"))
		functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
		self.assertTrue(
			{
				"create_supplier_profile",
				"transition_supplier_profile",
				"get_supplier_profile",
				"list_supplier_profiles",
			}.issubset(functions)
		)
		text = service_path.read_text(encoding="utf-8")
		for token in (
			"_resolve_chain",
			'role_type": "Supplier',
			"NXR Entity Compliance",
			"start_idempotency",
			"issue_document_number",
			"audit(",
			"service_write",
			".for_update()",
			"periods_overlap",
		):
			self.assertIn(token, text)
		self.assertNotIn('doctype": "Supplier"', text)

	def test_controller_and_permissions_enforce_server_boundary(self) -> None:
		controller = (DOCTYPE_ROOT / "nxr_supplier_profile/nxr_supplier_profile.py").read_text(
			encoding="utf-8"
		)
		self.assertIn("require_service_write", controller)
		self.assertIn("on_trash", controller)
		permissions = (PACKAGE / "permissions.py").read_text(encoding="utf-8")
		self.assertIn('"read_purchases"', permissions)
		self.assertIn('"create_supplier"', permissions)
		self.assertIn('"manage_supplier"', permissions)

	def test_supplier_page_and_workspace_are_connected(self) -> None:
		page_root = PACKAGE / "nexora/page/nexora_suppliers"
		page = json.loads((page_root / "nexora_suppliers.json").read_text(encoding="utf-8"))
		self.assertEqual("nexora-suppliers", page["name"])
		script = (page_root / "nexora_suppliers.js").read_text(encoding="utf-8")
		self.assertIn("nexora.purchases.service.create_supplier_profile", script)
		self.assertIn("nexora.purchases.service.transition_supplier_profile", script)
		self.assertIn("NXR Entity Compliance", script)
		workspace = json.loads((PACKAGE / "nexora/workspace/nexora/nexora.json").read_text(encoding="utf-8"))
		shortcuts = {(row["label"], row["type"], row["link_to"]) for row in workspace["shortcuts"]}
		self.assertIn(("Gestión de proveedores", "Page", "nexora-suppliers"), shortcuts)
		self.assertIn(("Perfiles de proveedor", "DocType", "NXR Supplier Profile"), shortcuts)

	def test_purchase_request_reuses_canonical_financial_dimensions(self) -> None:
		parent = json.loads(
			(DOCTYPE_ROOT / "nxr_purchase_request/nxr_purchase_request.json").read_text(encoding="utf-8")
		)
		line = json.loads(
			(DOCTYPE_ROOT / "nxr_purchase_request_line/nxr_purchase_request_line.json").read_text(
				encoding="utf-8"
			)
		)
		fields = {row["fieldname"]: row for row in parent["fields"]}
		line_fields = {row["fieldname"]: row for row in line["fields"]}
		self.assertEqual("NXR Purchase Request Line", fields["lines"]["options"])
		self.assertEqual("Project", fields["project"]["options"])
		self.assertEqual("Cost Center", fields["cost_center"]["options"])
		self.assertEqual("NXR Fund Source", fields["fund_source"]["options"])
		self.assertEqual("NXR Evidence", fields["evidence"]["options"])
		self.assertEqual("Item", line_fields["catalog_item"]["options"])
		self.assertEqual("UOM", line_fields["uom"]["options"])
		self.assertEqual("NXR Economic Category", line_fields["economic_category"]["options"])
		self.assertTrue(line_fields["estimated_amount"]["read_only"])

	def test_purchase_request_service_is_controlled_and_audited(self) -> None:
		path = PACKAGE / "purchases/request_service.py"
		text = path.read_text(encoding="utf-8")
		tree = ast.parse(text)
		functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
		self.assertTrue(
			{
				"create_purchase_request",
				"transition_purchase_request",
				"get_purchase_request",
				"list_purchase_requests",
			}.issubset(functions)
		)
		for token in (
			"issue_document_number",
			"start_idempotency",
			"service_write",
			".for_update()",
			"audit(",
			'"create_purchase_request"',
			'"approve_purchase_request"',
			'"NXR Economic Category"',
		):
			self.assertIn(token, text)
		controller = (DOCTYPE_ROOT / "nxr_purchase_request/nxr_purchase_request.py").read_text(
			encoding="utf-8"
		)
		self.assertIn("require_service_write", controller)
		self.assertIn("get_doc_before_save", controller)

	def test_financial_workflow_executes_purchase_runtime(self) -> None:
		workflow = (APP_ROOT.parent / ".github/workflows/nexora-financial.yml").read_text(encoding="utf-8")
		self.assertIn("test_purchase_core", workflow)
		self.assertIn("test_purchase_integration", workflow)
		self.assertIn("test_purchase_request_core", workflow)
		self.assertIn("test_purchase_request_integration", workflow)
		self.assertIn("nexora_suppliers.js", workflow)


if __name__ == "__main__":
	unittest.main()
