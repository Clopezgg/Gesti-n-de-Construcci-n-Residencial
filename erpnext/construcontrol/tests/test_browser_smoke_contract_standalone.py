from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "browser_smoke.mjs"
OVERRIDE = ROOT / "deploy" / "ci" / "docker-compose.browser.yml"


class BrowserSmokeContractTest(unittest.TestCase):
	def test_playwright_script_covers_desktop_iphone_routes_and_pwa(self) -> None:
		source = SCRIPT.read_text(encoding="utf-8")
		for token in (
			'from "playwright"',
			'devices["iPhone 13"]',
			"viewport: { width: 1440, height: 900 }",
			"/api/method/login",
			'navigator.serviceWorker.getRegistration("/")',
			"deploy-version.json",
			"data-cc-camera-gallery",
			"page.goBack",
			"page.screenshot",
			'currentRoute === "setup-wizard"',
			"was blocked by",
			"captureRouteFailure",
			"console_errors",
			"page_errors",
			"navigation_type",
			"locator(`#page-${route}`)",
			"Fresh PWA installation reloaded the page",
			'BROWSER_LOCALE || "es-HN"',
			"new Intl.Locale(browserLocale)",
			"locale: browserLocale",
			"navigator_language",
		):
			self.assertIn(token, source)
		for route in (
			"construcontrol-dashboard",
			"construcontrol-profile",
			"construcontrol-project-center",
			"construcontrol-users",
			"construcontrol-integrations",
			"construcontrol-reporting-center",
			"construcontrol-weekly-closing",
			"construcontrol-migration-console",
		):
			self.assertIn(f'"{route}"', source)

	def test_failure_evidence_is_persisted_before_the_profile_raises(self) -> None:
		source = SCRIPT.read_text(encoding="utf-8")
		self.assertIn("report.profiles.push(profile)", source)
		self.assertIn('status: "failed"', source)
		self.assertIn("diagnosticsPath", source)
		self.assertIn("await captureRouteFailure(page, profile, route, error)", source)
		self.assertLess(
			source.index("await captureRouteFailure(page, profile, route, error)"),
			source.index("throw error", source.index("await captureRouteFailure")),
		)

	def test_browser_compose_override_binds_only_loopback(self) -> None:
		source = OVERRIDE.read_text(encoding="utf-8")
		self.assertIn('"127.0.0.1:${BROWSER_PORT:-8080}:8080"', source)
		self.assertNotIn("0.0.0.0", source)


if __name__ == "__main__":
	unittest.main()
