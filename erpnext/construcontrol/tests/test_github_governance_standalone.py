from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[3] / "scripts" / "validate_github_governance.py"
SPEC = importlib.util.spec_from_file_location("validate_github_governance", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
	raise RuntimeError(f"Unable to load {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class GitHubGovernanceValidationTest(unittest.TestCase):
	def test_rejects_direct_main_push(self) -> None:
		path = Path("construcontrol-container-receipt.yml")
		violations = MODULE.workflow_violations(path, "run: git push origin HEAD:main\n")
		self.assertIn("direct push to main", violations)

	def test_rejects_remote_branch_deletion(self) -> None:
		path = Path("construcontrol-branch-cleanup.yml")
		violations = MODULE.workflow_violations(path, "run: git push origin --delete old-branch\n")
		self.assertIn("remote branch deletion", violations)

	def test_rejects_write_permission_in_controlled_workflow(self) -> None:
		path = Path("apply-construcontrol-consolidation.yml")
		violations = MODULE.workflow_violations(path, "permissions:\n  contents: write\n")
		self.assertIn("write permission in controlled ConstruControl workflow", violations)

	def test_accepts_read_only_artifact_workflow(self) -> None:
		path = Path("construcontrol-verification-receipt.yml")
		text = "permissions:\n  contents: read\nsteps:\n  - uses: actions/upload-artifact@v4\n"
		self.assertEqual(MODULE.workflow_violations(path, text), [])

	def test_repository_workflows_are_safe(self) -> None:
		self.assertEqual(MODULE.scan_workflows(), {})

	def test_scans_all_yaml_workflows(self) -> None:
		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			(root / "safe.yml").write_text("permissions:\n  contents: read\n", encoding="utf-8")
			(root / "unsafe.yaml").write_text("run: git push origin HEAD:main\n", encoding="utf-8")
			failures = MODULE.scan_workflows(root)
		self.assertEqual(list(failures), [(root / "unsafe.yaml").as_posix()])


if __name__ == "__main__":
	unittest.main()
