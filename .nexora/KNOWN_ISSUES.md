# NEXORA Known Issues

## OPEN
1. **[HIGH] NEXORA app CI failing - iPhone WebKit timeout**
   - Workflow: NEXORA app (run 30680012253 on 9d167c8)
   - scripts/nexora_browser_smoke.mjs openDetailTab() TimeoutError clicking `[data-detail-tab="amount"]` under WebKit + iPhone 13 device emulation.
   - Suspected cause: mobile CSS (.nxr-detail-tabs in nexora_operational.css) doesn't guarantee tab buttons stay clickable/visible at 390px width, or Playwright needs explicit scroll before click on WebKit engine specifically (chromium/desktop profiles pass).

2. **[HIGH] ConstruControl production validation failing**
   - Workflow failing on HEAD (run 30680012242). Logs expired before analysis - need re-run to capture live logs.

3. **[MEDIUM] .github/workflows/cr.yml failing**
   - Run 30680011915 failing on HEAD. Logs expired. Likely related to commit/PR title semantic validation (validate_commit_titles.py exists in scripts/) - needs verification.

4. **[MEDIUM] NEXORA predeploy certification receipt failing**
   - Run 30680012270 failing on HEAD. Possibly cascades from NEXORA app failure (predeploy gating).

## NOT YET AUDITED
- Sentry integration files (nexora_sentry.js, sentry.py, hooks.py) - not yet reviewed this session.
- Financial flow functions: applyMovement(), selectTab(), nexora_apply_operational_context(), movement_catalog, state.movements - not yet reviewed this session.
- Docker/docker-compose/Coolify/migrations - not yet reviewed this session.
