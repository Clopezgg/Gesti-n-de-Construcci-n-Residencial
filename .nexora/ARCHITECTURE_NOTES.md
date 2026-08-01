# NEXORA Architecture Notes

- Frappe/ERPNext-based app: nexora_app/nexora/nexora/ (doctype, page modules)
- Key operations page: nexora_app/nexora/nexora/page/nexora_operations/nexora_operations.js
  - Contains guided wizard for financial movements (expense/income), tab navigation via `.nxr-detail-tabs` buttons with `data-detail-tab` attributes (e.g. "account", "amount").
  - selectTab(group, name) at line 424 handles in-app tab switching logic.
- Styling: nexora_app/nexora/public/css/nexora_operational.css
  - Responsive breakpoints via @media queries; mobile block at max-width:575px (lines 396-441).
- Browser/E2E smoke tests: scripts/nexora_browser_smoke.mjs (Playwright, ESM)
  - runProfile() executes full validation across multiple device/browser profiles (desktop-chromium, iphone-13-webkit, others) - each profile: launches browser, opens app, runs validateGuidedOperations -> validateExpenseGuided/validateIncomeGuided etc., asserts no console/server/auth errors, captures failure screenshots via captureFailure() on error.
  - Helper: openDetailTab(page, name) - locates and clicks `[data-detail-tab="name"]`.
  - Helper: setField(page, name, value) - sets form field value (select or input/textarea).
- CI/CD: GitHub Actions workflows in .github/workflows/ include NEXORA app, NEXORA governance, Linters, NEXORA financial invariants, ConstruControl production validation, NEXORA predeploy certification receipt, cr.yml (commit/PR validation), NEXORA final acceptance and delivery.
- gh CLI is available and authenticated in this Codespace for querying Actions runs/logs directly.
