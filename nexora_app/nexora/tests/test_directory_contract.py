from __future__ import annotations

import ast
import json
import pathlib
import unittest

APP_ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKAGE = APP_ROOT / "nexora"
DOCTYPE_ROOT = PACKAGE / "nexora/doctype"

DIRECTORY_MODELS = {
	"nxr_entity": "NXR Entity",
	"nxr_entity_identifier": "NXR Entity Identifier",
	"nxr_entity_contact": "NXR Entity Contact",
	"nxr_entity_role": "NXR Entity Role",
	"nxr_entity_compliance": "NXR Entity Compliance",
	"nxr_entity_consolidation": "NXR Entity Consolidation",
}


class TestDirectoryContract(unittest.TestCase):
	def test_all_directory_models_are_real_nexora_doctypes_with_controllers(self) -> None:
		for folder, doctype in DIRECTORY_MODELS.items():
			root = DOCTYPE_ROOT / folder
			definition = json.loads((root / f"{folder}.json").read_text(encoding="utf-8"))
			self.assertEqual(doctype, definition["name"])
			self.assertEqual("NEXORA", definition["module"])
			self.assertTrue((root / f"{folder}.py").is_file())

	def test_sensitive_child_values_are_password_fields_and_not_exportable(self) -> None:
		for folder, fieldname in (
			("nxr_entity_identifier", "identifier_value"),
			("nxr_entity_contact", "contact_value"),
		):
			definition = json.loads((DOCTYPE_ROOT / folder / f"{folder}.json").read_text(encoding="utf-8"))
			fields = {row["fieldname"]: row for row in definition["fields"]}
			self.assertEqual("Password", fields[fieldname]["fieldtype"])
			self.assertEqual(1, fields[fieldname]["permlevel"])
			self.assertTrue(fields["normalized_hash"]["read_only"])

	def test_entity_and_related_records_are_service_write_only_and_non_deletable(self) -> None:
		for folder in DIRECTORY_MODELS:
			controller = (DOCTYPE_ROOT / folder / f"{folder}.py").read_text(encoding="utf-8")
			self.assertIn("require_service_write()", controller)
			if folder not in {"nxr_entity_identifier", "nxr_entity_contact"}:
				self.assertIn("def on_trash", controller)
		entity_controller = (DOCTYPE_ROOT / "nxr_entity/nxr_entity.py").read_text(encoding="utf-8")
		self.assertIn("La entidad terminal es inmutable", entity_controller)
		self.assertIn("merged_into", entity_controller)
		self.assertIn("consolidation_record", entity_controller)

	def test_public_api_exports_complete_server_side_directory(self) -> None:
		api = (PACKAGE / "directory/api.py").read_text(encoding="utf-8")
		service = (PACKAGE / "directory/service.py").read_text(encoding="utf-8")
		for function in (
			"create_entity",
			"update_entity",
			"transition_entity",
			"get_entity",
			"search_entities",
			"detect_entity_duplicates",
			"assign_entity_role",
			"transition_entity_role",
			"create_entity_compliance",
			"transition_entity_compliance",
			"consolidate_entities",
			"resolve_canonical_entity",
		):
			self.assertIn(f"def {function}", service)
			self.assertIn(f"{function} = _service.{function}", api)
			self.assertIn('@frappe.whitelist(methods=["POST"])', service)

		locks = (PACKAGE / "directory/lock_helpers.py").read_text(encoding="utf-8")
		consolidation = (PACKAGE / "directory/consolidation_service.py").read_text(encoding="utf-8")
		reads = (PACKAGE / "directory/entity_read_service.py").read_text(encoding="utf-8")
		common = (PACKAGE / "directory/common.py").read_text(encoding="utf-8")
		self.assertIn("for_update()", locks)
		self.assertIn("FOR UPDATE", locks)
		self.assertIn('entity.linked_user == linked_user', locks)
		self.assertIn('entity.status != "Consolidated"', locks)
		self.assertIn("preserved_references", consolidation)
		self.assertIn("read_sensitive_entity", reads)
		self.assertIn("_lock_identifier_hashes", common)

	def test_permissions_are_enforced_by_action_and_sensitive_read_is_restricted(self) -> None:
		permissions = (PACKAGE / "permissions.py").read_text(encoding="utf-8")
		for action in (
			"read_entities",
			"read_sensitive_entity",
			"create_entity",
			"update_entity",
			"manage_entity",
			"manage_entity_role",
			"manage_entity_compliance",
			"consolidate_entity",
		):
			self.assertIn(f'"{action}"', permissions)
		self.assertIn("SENSITIVE_DIRECTORY_ROLES", permissions)
		self.assertNotIn(
			'"NEXORA Project Viewer",\n}',
			permissions.split("SENSITIVE_DIRECTORY_ROLES", 1)[1].split("}", 1)[0],
		)

	def test_page_and_workspace_are_connected_to_real_services(self) -> None:
		page_root = PACKAGE / "nexora/page/nexora_entities"
		definition = json.loads((page_root / "nexora_entities.json").read_text(encoding="utf-8"))
		javascript = (page_root / "nexora_entities.js").read_text(encoding="utf-8")
		self.assertEqual("nexora-entities", definition["name"])
		for service in (
			"create_entity",
			"search_entities",
			"detect_entity_duplicates",
			"assign_entity_role",
			"create_entity_compliance",
			"transition_entity_compliance",
			"consolidate_entities",
		):
			self.assertIn(f"nexora.directory.service.{service}", javascript)
		workspace = json.loads((PACKAGE / "nexora/workspace/nexora/nexora.json").read_text(encoding="utf-8"))
		shortcuts = {(row["label"], row["type"], row["link_to"]) for row in workspace["shortcuts"]}
		self.assertIn(("Directorio de entidades", "Page", "nexora-entities"), shortcuts)
		self.assertIn(("Entidades", "DocType", "NXR Entity"), shortcuts)

	def test_service_and_page_parse_without_syntax_errors(self) -> None:
		ast.parse((PACKAGE / "directory/service.py").read_text(encoding="utf-8"))
		ast.parse((PACKAGE / "directory/api.py").read_text(encoding="utf-8"))

	def test_permanent_workflows_include_directory_runtime_and_pure_tests(self) -> None:
		app = (APP_ROOT.parent / ".github/workflows/nexora-app.yml").read_text(encoding="utf-8")
		financial = (APP_ROOT.parent / ".github/workflows/nexora-financial.yml").read_text(encoding="utf-8")
		for text in (app, financial):
			self.assertIn("test_directory_core", text)
			self.assertIn("nexora_entities.js", text)
		self.assertIn("test_directory_integration", financial)
		self.assertIn("directory_concurrency_probe.run", financial)


if __name__ == "__main__":
	unittest.main()
