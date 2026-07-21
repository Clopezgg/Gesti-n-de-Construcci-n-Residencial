from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "migration" / "runtime_contract.py"
SPEC = importlib.util.spec_from_file_location("construcontrol_runtime_contract", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
	raise RuntimeError(f"Unable to load {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

validate_runtime_contract = MODULE.validate_runtime_contract


def write_runtime(root: Path, definitions: list[dict], assets: dict | None = None) -> None:
	root.mkdir(parents=True, exist_ok=True)
	(root / "definitions_core.json").write_text(json.dumps(definitions), encoding="utf-8")
	(root / "assets.json").write_text(
		json.dumps(
			assets
			or {
				"pages": [{"name": "construcontrol-dashboard", "page_name": "construcontrol-dashboard"}],
				"reports": [{"name": "CC Estado", "ref_doctype": "CC Example"}],
				"print_formats": [{"name": "CC Example Print", "doc_type": "CC Example"}],
			}
		),
		encoding="utf-8",
	)


def valid_definition() -> dict:
	return {
		"name": "CC Example",
		"custom": 1,
		"fields": [
			{"fieldname": "source_key", "label": "Source Key", "fieldtype": "Data", "unique": 1},
			{"fieldname": "source_id", "label": "Source ID", "fieldtype": "Data"},
			{"fieldname": "payload_json", "label": "Payload", "fieldtype": "Long Text"},
			{"fieldname": "is_logically_deleted", "label": "Deleted", "fieldtype": "Check"},
			{"fieldname": "project", "label": "Project", "fieldtype": "Link", "options": "Project"},
		],
	}


class RuntimeContractTest(unittest.TestCase):
	def test_accepts_safe_idempotent_contract(self) -> None:
		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			write_runtime(root, [valid_definition()])
			report = validate_runtime_contract(root, required_doctypes={"CC Example"})
			self.assertTrue(report["ok"], report)
			self.assertEqual(report["doctype_count"], 1)
			self.assertEqual(report["warnings"], [])
			self.assertRegex(report["sha256"], r"^[a-f0-9]{64}$")

	def test_rejects_duplicate_fields_and_destructive_keys(self) -> None:
		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			definition = valid_definition()
			definition["fields"].append(
				{"fieldname": "source_key", "label": "Duplicate", "fieldtype": "Data"}
			)
			definition["drop_table"] = True
			write_runtime(root, [definition])
			report = validate_runtime_contract(root, required_doctypes={"CC Example"})
			self.assertFalse(report["ok"])
			self.assertTrue(any("fieldname duplicado" in error for error in report["errors"]))
			self.assertTrue(any("operaciones destructivas" in error for error in report["errors"]))

	def test_rejects_standard_erpnext_doctype_mutation(self) -> None:
		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			definition = valid_definition()
			definition["name"] = "Sales Invoice"
			write_runtime(root, [definition])
			report = validate_runtime_contract(root, required_doctypes={"Sales Invoice"})
			self.assertFalse(report["ok"])
			self.assertTrue(any("DocType estándar" in error for error in report["errors"]))

	def test_rejects_missing_provenance_for_import_targets(self) -> None:
		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			definition = valid_definition()
			definition["fields"] = [{"fieldname": "title", "label": "Title", "fieldtype": "Data"}]
			write_runtime(root, [definition])
			report = validate_runtime_contract(root, required_doctypes={"CC Example"})
			self.assertFalse(report["ok"])
			self.assertTrue(any("campos de trazabilidad" in error for error in report["errors"]))

	def test_rejects_duplicate_assets(self) -> None:
		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			assets = {
				"pages": [
					{"name": "construcontrol-dashboard", "page_name": "construcontrol-dashboard"},
					{"name": "construcontrol-dashboard", "page_name": "construcontrol-dashboard"},
				],
				"reports": [],
				"print_formats": [],
			}
			write_runtime(root, [valid_definition()], assets)
			report = validate_runtime_contract(root)
			self.assertFalse(report["ok"])
			self.assertTrue(any("pages duplicado" in error for error in report["errors"]))


if __name__ == "__main__":
	unittest.main()
