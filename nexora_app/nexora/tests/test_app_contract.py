from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import tempfile
import unittest

APP_ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKAGE = APP_ROOT / "nexora"


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

	def test_apps_registry_is_idempotent_without_trailing_newline(self) -> None:
		module_path = APP_ROOT.parent / "scripts/register_nexora_app.py"
		spec = importlib.util.spec_from_file_location("register_nexora_app", module_path)
		if spec is None or spec.loader is None:
			raise RuntimeError(f"Unable to load {module_path}")
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
		with tempfile.TemporaryDirectory() as directory:
			apps_file = pathlib.Path(directory) / "apps.txt"
			apps_file.write_text("frappe\npayments", encoding="utf-8")
			module.register_app(apps_file)
			module.register_app(apps_file)
			self.assertEqual("frappe\npayments\nnexora\n", apps_file.read_text(encoding="utf-8"))

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
