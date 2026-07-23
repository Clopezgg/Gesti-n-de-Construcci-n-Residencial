from __future__ import annotations

import ast
import importlib.util
import json
import pathlib
import re
import tempfile
import unittest
from unittest.mock import patch

APP_ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKAGE = APP_ROOT / "nexora"


def _load_register_module():
	module_path = APP_ROOT.parent / "scripts/register_nexora_app.py"
	spec = importlib.util.spec_from_file_location("register_nexora_app", module_path)
	if spec is None or spec.loader is None:
		raise RuntimeError(f"Unable to load {module_path}")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


def _called_names(function: ast.FunctionDef) -> set[str]:
	return {
		node.func.id
		for node in ast.walk(function)
		if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
	}


class TestNexoraAppContract(unittest.TestCase):
	def test_required_scaffold_exists(self) -> None:
		required = [
			APP_ROOT / "pyproject.toml",
			PACKAGE / "hooks.py",
			PACKAGE / "modules.txt",
			PACKAGE / "install.py",
			PACKAGE / "permissions.py",
			PACKAGE / "nexora/workspace/nexora/nexora.json",
			PACKAGE / "fixtures/role.json",
		]
		self.assertEqual([], [str(path) for path in required if not path.is_file()])

	def test_doctype_package_and_module_declarations_are_installable(self) -> None:
		doctype_root = PACKAGE / "nexora/doctype"
		self.assertTrue((doctype_root / "__init__.py").is_file())
		definitions = sorted(doctype_root.glob("*/*.json"))
		self.assertEqual(10, len(definitions))
		for definition in definitions:
			payload = json.loads(definition.read_text(encoding="utf-8"))
			self.assertEqual("NEXORA", payload["module"], definition)
			self.assertTrue(definition.with_suffix(".py").is_file(), definition)

	def test_apps_registry_is_idempotent_without_trailing_newline(self) -> None:
		module = _load_register_module()
		with tempfile.TemporaryDirectory() as directory:
			apps_file = pathlib.Path(directory) / "apps.txt"
			apps_file.write_text("frappe\npayments", encoding="utf-8")
			module.register_app(apps_file)
			module.register_app(apps_file)
			self.assertEqual("frappe\npayments\nnexora\n", apps_file.read_text(encoding="utf-8"))

	def test_apps_registry_change_invalidates_frappe_module_cache(self) -> None:
		module = _load_register_module()
		with tempfile.TemporaryDirectory() as directory:
			bench = pathlib.Path(directory) / "frappe-bench"
			(bench / "apps").mkdir(parents=True)
			(bench / "sites").mkdir()
			apps_file = bench / "sites/apps.txt"
			apps_file.write_text("frappe\nerpnext\n", encoding="utf-8")
			with patch.object(module, "_run") as run:
				module.register_app(apps_file)
			run.assert_called_once_with("bench", "--site", "all", "clear-cache", cwd=bench)

	def test_catalog_seed_runs_only_after_doctype_sync(self) -> None:
		hooks = (PACKAGE / "hooks.py").read_text(encoding="utf-8")
		self.assertIn('after_migrate = "nexora.install.after_migrate"', hooks)
		tree = ast.parse((PACKAGE / "install.py").read_text(encoding="utf-8"))
		functions = {
			node.name: node
			for node in tree.body
			if isinstance(node, ast.FunctionDef) and node.name in {"after_install", "after_migrate"}
		}
		self.assertEqual({"after_install", "after_migrate"}, set(functions))
		self.assertNotIn("seed_analytic_catalogs", _called_names(functions["after_install"]))
		self.assertIn("_ensure_sequence_counter", _called_names(functions["after_install"]))
		self.assertIn("seed_analytic_catalogs", _called_names(functions["after_migrate"]))
		self.assertNotIn("_ensure_sequence_counter", _called_names(functions["after_migrate"]))
		self.assertNotIn("create_sequence_counter", _called_names(functions["after_migrate"]))

	def test_identity_and_dependency_are_explicit(self) -> None:
		hooks = (PACKAGE / "hooks.py").read_text(encoding="utf-8")
		self.assertIn('app_name = "nexora"', hooks)
		self.assertIn('app_title = "NEXORA"', hooks)
		self.assertIn('required_apps = ["erpnext"]', hooks)

	def test_new_app_has_no_legacy_import_or_visible_brand(self) -> None:
		findings: list[str] = []
		for path in APP_ROOT.rglob("*"):
			if path.is_file() and path.suffix in {".py", ".json", ".js", ".css", ".md", ".toml"}:
				text = path.read_text(encoding="utf-8")
				if re.search(r"(?:import|from)\s+erpnext\.construcontrol", text, re.IGNORECASE):
					findings.append(str(path))
		self.assertEqual([], findings)
		workspace = (PACKAGE / "nexora/workspace/nexora/nexora.json").read_text(encoding="utf-8")
		self.assertNotIn("ConstruControl", workspace)
		self.assertNotIn("ERPNext", workspace)

	def test_roles_and_workspace_are_consistent(self) -> None:
		roles = json.loads((PACKAGE / "fixtures/role.json").read_text(encoding="utf-8"))
		names = {row["name"] for row in roles}
		workspace = json.loads((PACKAGE / "nexora/workspace/nexora/nexora.json").read_text(encoding="utf-8"))
		workspace_roles = {row["role"] for row in workspace["roles"]}
		self.assertEqual(names, workspace_roles)
		self.assertEqual("NEXORA", workspace["title"])


if __name__ == "__main__":
	unittest.main()
