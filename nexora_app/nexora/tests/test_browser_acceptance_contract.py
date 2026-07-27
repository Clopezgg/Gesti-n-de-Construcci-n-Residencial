from __future__ import annotations

import pathlib
import unittest

import nexora

REPO_ROOT = pathlib.Path(nexora.__file__).resolve().parents[2]
BROWSER_FILES = (
	"nexora_browser_support.mjs",
	"nexora_browser_validators.mjs",
	"nexora_browser_smoke.mjs",
)


def _browser_code() -> str:
	return "\n".join(
		(REPO_ROOT / "scripts" / filename).read_text(encoding="utf-8") for filename in BROWSER_FILES
	)


class TestBrowserAcceptanceContract(unittest.TestCase):
	def test_browser_suite_covers_executive_surfaces(self) -> None:
		code = _browser_code()
		for marker in (
			'"nexora-dashboard"',
			'"nexora-reports"',
			'"nexora-closing"',
			'"desktop-chromium"',
			'"iphone-13-webkit"',
			"validateDashboard",
			"validateReports",
			"validateClosing",
			"validatePwa",
			"validateResponsiveLayout",
			"bounded_operational_queries",
			"nexora-analytics-v3",
		):
			self.assertIn(marker, code)

	def test_quick_actions_use_the_current_single_handler_contract(self) -> None:
		code = _browser_code()
		self.assertIn('[data-action="expense"]', code)
		self.assertIn('[data-action="income"]', code)
		self.assertNotIn('[data-route="nexora-finance"][data-action="expense"]', code)
		self.assertNotIn('[data-route="nexora-finance"][data-action="income"]', code)

	def test_global_navigation_never_reuses_a_page_product_shell(self) -> None:
		code = (REPO_ROOT / "nexora_app/nexora/public/js/nexora.js").read_text(encoding="utf-8")
		self.assertIn('document.querySelector(".nxr-product-navigation")', code)
		self.assertIn('shell.className = "nxr-product-shell nxr-product-navigation"', code)
		self.assertNotIn('document.querySelector(".nxr-product-shell")', code)

	def test_runtime_image_does_not_patch_application_source(self) -> None:
		dockerfile = (REPO_ROOT / "Dockerfile.nexora").read_text(encoding="utf-8")
		dashboard = (
			REPO_ROOT / "nexora_app/nexora/nexora/page/nexora-dashboard/nexora-dashboard.js"
		).read_text(encoding="utf-8")
		navigation = (REPO_ROOT / "nexora_app/nexora/public/js/nexora.js").read_text(
			encoding="utf-8"
		)
		validators = (REPO_ROOT / "scripts/nexora_browser_validators.mjs").read_text(
			encoding="utf-8"
		)
		self.assertNotIn("sed -i", dockerfile)
		self.assertNotIn("RUN python3 -c", dockerfile)
		self.assertIn('loading="eager"', dashboard)
		self.assertIn("[0, 50, 150, 300, 600, 1000]", navigation)
		self.assertIn("h2.nxr-project-name", validators)

	def test_browser_suite_calculates_but_does_not_persist_a_weekly_close(self) -> None:
		code = _browser_code()
		self.assertIn(".nxr-calculate", code)
		self.assertNotIn("save_weekly_close", code)
		self.assertNotIn("correct_weekly_close", code)


if __name__ == "__main__":
	unittest.main()
