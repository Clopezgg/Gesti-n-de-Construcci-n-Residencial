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
			REPO_ROOT / "nexora_app/nexora/nexora/page/nexora_dashboard/nexora_dashboard.js"
		).read_text(encoding="utf-8")
		navigation = (REPO_ROOT / "nexora_app/nexora/public/js/nexora.js").read_text(encoding="utf-8")
		validators = (REPO_ROOT / "scripts/nexora_browser_validators.mjs").read_text(encoding="utf-8")
		self.assertNotIn("sed -i", dockerfile)
		self.assertNotIn("RUN python3 -c", dockerfile)
		self.assertIn('loading="eager"', dashboard)
		self.assertIn("[0, 50, 150, 300, 600, 1000]", navigation)
		self.assertIn("h2.nxr-project-name", validators)

	def test_route_wait_uses_rendered_state_and_publishes_diagnostics(self) -> None:
		code = (REPO_ROOT / "scripts/nexora_browser_support.mjs").read_text(encoding="utf-8")
		self.assertIn("did not reach a stable rendered state", code)
		self.assertIn("frappe_route", code)
		self.assertIn("page_visible", code)
		self.assertIn("routeSnapshot = await handle.jsonValue()", code)
		self.assertNotIn("page.locator(`#page-${route}`).innerText()", code)
		self.assertNotIn("locator(`#page-${route} .nxr-product-shell`)", code)

	def test_browser_network_calls_and_process_have_explicit_deadlines(self) -> None:
		support = (REPO_ROOT / "scripts/nexora_browser_support.mjs").read_text(encoding="utf-8")
		smoke = (REPO_ROOT / "scripts/nexora_browser_smoke.mjs").read_text(encoding="utf-8")
		workflow = (REPO_ROOT / ".github/workflows/nexora-app.yml").read_text(encoding="utf-8")
		self.assertIn("NEXORA_BROWSER_REQUEST_TIMEOUT_MS", support)
		self.assertIn("const response = await page", support)
		self.assertIn(".context()\n    .request.fetch", support)
		self.assertIn("timeout: browserRequestTimeoutMs", support)
		self.assertNotIn("AbortController", support)
		self.assertIn("const response = await postArgs", smoke)
		self.assertNotIn(
			"return page.evaluate(", smoke.split("async function callFrappe", 1)[1].split("}", 1)[0]
		)
		self.assertIn("browserRequest(page, response.url()", smoke)
		self.assertIn("postArgs(", (REPO_ROOT / "scripts/nexora_browser_validators.mjs").read_text())
		self.assertNotIn("window.frappe.call", _browser_code().split("async function callFrappe", 1)[0])
		self.assertNotIn(
			"window.frappe.call", (REPO_ROOT / "scripts/nexora_browser_validators.mjs").read_text()
		)
		self.assertIn("kill-after=30s 10m", workflow)
		self.assertIn("kill-after=30s 20m", workflow)
		self.assertIn("timeout --signal=INT --kill-after=30s 50m", workflow)

	def test_global_context_observer_is_idempotent_and_frame_coalesced(self) -> None:
		code = (REPO_ROOT / "nexora_app/nexora/public/js/nexora_report_actions.js").read_text(
			encoding="utf-8"
		)
		for marker in (
			"function setText(node, value)",
			"if (node.textContent === text) return;",
			"new MutationObserver(scheduleEnhancements)",
			"function scheduleEnhancements()",
			"if (observerFrame !== null) return;",
			"observerFrame = window.requestAnimationFrame",
		):
			self.assertIn(marker, code)
		self.assertNotIn(
			'querySelector("[data-nexora-context-user]").textContent =',
			code,
		)

	def test_guided_review_waits_for_stable_network_and_idempotent_rendering(self) -> None:
		smoke = (REPO_ROOT / "scripts/nexora_browser_smoke.mjs").read_text(encoding="utf-8")
		guided = (REPO_ROOT / "nexora_app/nexora/public/js/nexora_guided_operations.js").read_text(
			encoding="utf-8"
		)
		for marker in (
			"waitForOperationalQuiescence",
			'page.waitForLoadState("networkidle"',
			"advanceValidatedGuidedReview",
			"__nexoraGuidedReviewProbe",
			"now - probe.since >= stableForMs",
		):
			self.assertIn(marker, smoke)
		for marker in (
			"target.dataset.accountSignature === signature",
			"if (review.innerHTML !== reviewHtml)",
			"if (node.hidden !== hidden)",
			"if (next.disabled === valid)",
			"if (execute.disabled === valid)",
		):
			self.assertIn(marker, guided)
		self.assertNotIn("if (target) target.innerHTML = accountMarkup(state)", guided)

	def test_dashboard_gate_requires_context_actions_and_clean_console(self) -> None:
		code = (REPO_ROOT / "scripts/nexora_browser_validators.mjs").read_text(encoding="utf-8")
		for marker in (
			'.nxr-dashboard-shell[data-state="ready"]',
			".nxr-project-name",
			".nxr-dashboard-period",
			'[data-action="income"]',
			'[data-action="expense"]',
			"Dashboard bootstrap emitted page errors",
			"Dashboard bootstrap emitted console errors",
		):
			self.assertIn(marker, code)

	def test_browser_suite_calculates_but_does_not_persist_a_weekly_close(self) -> None:
		code = _browser_code()
		self.assertIn(".nxr-calculate", code)
		self.assertNotIn("save_weekly_close", code)
		self.assertNotIn("correct_weekly_close", code)

	def test_browser_suite_executes_search_correction_and_idempotent_replay(self) -> None:
		code = _browser_code()
		for marker in (
			"replayExecution",
			"universal_search_consolidated",
			"get_search_result_detail",
			"validateControlledCorrection",
			'"Anular operación"',
			'"nexora.operator@example.test"',
			'"nexora.manager@example.test"',
			'"Compensated"',
			"original_preserved: true",
		):
			self.assertIn(marker, code)


if __name__ == "__main__":
	unittest.main()
