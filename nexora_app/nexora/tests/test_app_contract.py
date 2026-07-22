from __future__ import annotations

import json
import pathlib
import re
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
        workspace = json.loads(
            (PACKAGE / "nexora/workspace/nexora/nexora.json").read_text(encoding="utf-8")
        )
        workspace_roles = {row["role"] for row in workspace["roles"]}
        self.assertEqual(names, workspace_roles)
        self.assertEqual("NEXORA", workspace["title"])


if __name__ == "__main__":
    unittest.main()
