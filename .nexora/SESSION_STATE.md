# NEXORA Recovery - Session State

Last updated: 2026-07-31 21:00 CST

## Repo
- Branch: main, HEAD: 9d167c8 (clean working tree at session start)
- Remote CI: GitHub Actions via `gh` CLI (authenticated)

## Latest CI results on HEAD (9d167c8)
- success: NEXORA governance (30680012230)
- success: NEXORA final acceptance and delivery (30680012255)
- success: Linters (30680012257)
- FAILURE: NEXORA app (30680012253)
- FAILURE: ConstruControl production validation (30680012242)
- success: NEXORA financial invariants (30680012220)
- FAILURE: NEXORA predeploy certification receipt (30680012270)
- FAILURE: .github/workflows/cr.yml (30680011915)

## Root cause found (NEXORA app / browser smoke failure)
File: scripts/nexora_browser_smoke.mjs
- Playwright profile "Validate desktop, iPhone WebKit and PWA2" (webkit, device "iPhone 13") times out.
- Failure chain: runProfile -> validateGuidedOperations -> validateExpenseGuided (line 594) -> openDetailTab (line 159:15) -> TimeoutError waiting to click `[data-detail-tab="amount"]`.
- openDetailTab implementation (lines 156-163):
  locates `[data-detail-tab="${name}"]` inside nav.nxr-detail-tabs and clicks first match; on iPhone WebKit viewport (390x844) the tab button is present but click times out, likely hidden/overlapped or outside viewport due to mobile CSS.
- CSS: nexora_app/nexora/public/css/nexora_operational.css
  - `.nxr-detail-tabs` base style at line 63 (flex nav, overflow-x auto at small width per line ~72)
  - `@media (max-width: 575px)` block starts at line 396, ends ~441; includes `.nxr-document-tabs, .nxr-detail-tabs { padding: 0 0.5rem; }` at line 439-441
  - No explicit `display:none` found for detail-tabs in mobile block, so hypothesis: tab bar overflows/scrolls horizontally and target button is out of the visible scroll area on iPhone 13 viewport, OR tab element needs scrollIntoView before click on WebKit.
- HTML source (nexora_operations.js lines ~93-95): `<nav class="nxr-detail-tabs">` contains buttons `data-detail-tab="account"` and `data-detail-tab="amount"`.

## Next concrete fix candidates (NOT YET APPLIED)
1. In scripts/nexora_browser_smoke.mjs `openDetailTab`, add `.scrollIntoViewIfNeeded()` before `.click()` and/or use `{ force: true }` fallback, OR increase actionability wait.
2. In nexora_operational.css mobile block, ensure `.nxr-detail-tabs` has `overflow-x:auto; -webkit-overflow-scrolling:touch;` and buttons have `flex:0 0 auto` so they don't collapse to zero width on narrow WebKit viewport.
3. Re-run only the NEXORA app workflow (or local `node scripts/nexora_browser_smoke.mjs`) to confirm fix.

## Other failing workflows (logs expired, need re-trigger to get fresh logs)
- ConstruControl production validation: log not available (gh run view --log-failed returned "log not found" / empty for old runs). Need to re-run workflow to capture fresh logs.
- .github/workflows/cr.yml (Semantic Commits / commit title validation likely): log expired too on run 30680011915.
- NEXORA predeploy certification receipt: depends on NEXORA app passing first (likely cascading failure).

## Environment note
Codespace connection dropped once mid-session (reconnected successfully, working tree unaffected, no data loss). gh CLI auth still valid after reconnect.
