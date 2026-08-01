# NEXORA Task Queue

## In progress
- [ ] Fix iPhone WebKit timeout in scripts/nexora_browser_smoke.mjs openDetailTab (root cause of NEXORA app failure)

## Pending (priority order)
1. [ ] Apply fix to openDetailTab / mobile CSS for .nxr-detail-tabs
2. [ ] Re-run/validate NEXORA app workflow locally before pushing
3. [ ] Investigate ConstruControl production validation failure (need fresh logs - re-trigger workflow)
4. [ ] Investigate .github/workflows/cr.yml failure (likely semantic commit / cr validation - need fresh logs)
5. [ ] Re-check NEXORA predeploy certification receipt (likely cascades from NEXORA app fix)
6. [ ] Audit Sentry integration (nexora_sentry.js, sentry.py, hooks.py)
7. [ ] Validate financial flow: applyMovement(), selectTab(), nexora_apply_operational_context(), movement_catalog, state.movements
8. [ ] Full test pass: Playwright profiles (desktop-chromium, iPhone WebKit+PWA2, others), Frappe validations
9. [ ] Production checks: Docker, docker-compose, migrations, Coolify config, security review
10. [ ] Repository cleanup: stale branches, duplicate workflows

## Completed
- [x] Created .nexora/ persistent state infrastructure
- [x] Pulled git status/log/branches/stash (clean tree, no stashes)
- [x] Pulled GitHub Actions run list (20 most recent runs on main)
- [x] Identified root cause of NEXORA app failure via full failure log analysis
