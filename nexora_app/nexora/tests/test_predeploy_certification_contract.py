from __future__ import annotations

import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent
REPOSITORY_ROOT = APP_ROOT.parents[1]


class TestPredeployCertificationContract(unittest.TestCase):
	def test_every_main_head_runs_every_permanent_certification_gate(self) -> None:
		for filename in (
			"linters.yml",
			"nexora-app.yml",
			"nexora-financial.yml",
			"nexora-final-delivery.yml",
			"nexora-predeploy-certification.yml",
		):
			workflow = (REPOSITORY_ROOT / ".github/workflows" / filename).read_text(encoding="utf-8")
			lines = workflow.splitlines()
			push_start = lines.index("  push:")
			push_block = []
			for line in lines[push_start + 1 :]:
				if line.startswith("  ") and not line.startswith("    "):
					break
				push_block.append(line)
			self.assertIn("    branches: [main]", push_block, filename)
			self.assertFalse(any(line.strip() == "paths:" for line in push_block), filename)

	def test_receipt_requires_every_mandatory_gate(self) -> None:
		workflow = (REPOSITORY_ROOT / ".github/workflows/nexora-predeploy-certification.yml").read_text(
			encoding="utf-8"
		)
		for gate in (
			"linters",
			"semgrep",
			"secrets",
			"contract",
			"install-rollback",
			"Frappe real · escritorio · iPhone · PWA",
			"mariadb",
			"Operational acceptance · Phases 2 and 3",
			"Verified final package",
		):
			self.assertIn(f'"{gate}"', workflow)
		self.assertIn("statuses: write", workflow)
		self.assertIn("checks: read", workflow)
		self.assertIn('context: "NEXORA Predeploy Certification"', workflow)
		self.assertIn('const accepted = new Set(["success"])', workflow)
		self.assertIn("if (!unresolved.length) break", workflow)
		self.assertIn("nexora-predeploy-certification-${{ github.sha }}", workflow)

	def test_quality_workflow_runs_precommit_twice_semgrep_and_secret_scan(self) -> None:
		workflow = (REPOSITORY_ROOT / ".github/workflows/linters.yml").read_text(encoding="utf-8")
		self.assertGreaterEqual(workflow.count("pre-commit run --all-files"), 2)
		self.assertIn("semgrep scan --error", workflow)
		self.assertIn("python scripts/scan_nexora_secrets.py", workflow)
		self.assertIn("git status --short", workflow)
		self.assertIn("test ! -s", workflow)

	def test_clean_install_mariadb_browser_and_pwa_are_permanent(self) -> None:
		app = (REPOSITORY_ROOT / ".github/workflows/nexora-app.yml").read_text(encoding="utf-8")
		financial = (REPOSITORY_ROOT / ".github/workflows/nexora-financial.yml").read_text(encoding="utf-8")
		for marker in (
			"bench --site test_site install-app nexora",
			"bench --site test_site migrate",
			"bench --site test_site uninstall-app nexora --yes",
			"playwright@1.52.0",
			"chromium webkit",
			"nexora_browser_smoke.mjs",
		):
			self.assertIn(marker, app)
		self.assertIn("mariadb:10.6", app)
		self.assertIn("test_guided_account_progressive_integration", financial)

	def test_browser_smoke_executes_guided_income_and_expense(self) -> None:
		smoke = (REPOSITORY_ROOT / "scripts/nexora_browser_smoke.mjs").read_text(encoding="utf-8")
		for marker in (
			"validateIncomeGuided",
			"validateExpenseGuided",
			"desktop-chromium",
			"iphone-13-webkit",
			"execute_operational_movement",
			"preview_operational_movement",
			"/^\\d{12}$/",
			"technical_account_labels_visible: false",
		):
			self.assertIn(marker, smoke)
		self.assertNotIn("validateFundSelector", smoke)
		self.assertNotIn("window.__nexoraExpenseDialog", smoke)


if __name__ == "__main__":
	unittest.main()
