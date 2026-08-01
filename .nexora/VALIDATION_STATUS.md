# NEXORA Validation Status

## GitHub Actions (as of HEAD 9d167c8)
| Workflow | Status |
|---|---|
| NEXORA governance | PASS |
| NEXORA final acceptance and delivery | PASS |
| Linters | PASS |
| NEXORA financial invariants | PASS |
| NEXORA app | FAIL (iPhone WebKit timeout, root cause known) |
| ConstruControl production validation | FAIL (logs expired, needs re-run) |
| NEXORA predeploy certification receipt | FAIL (likely cascades from NEXORA app) |
| .github/workflows/cr.yml | FAIL (logs expired, needs re-run) |

## Local validation
- Not yet run locally this session (no local Playwright run executed yet; analysis based on downloaded CI logs only).

## Sentry / Financial / Docker / Coolify
- Not yet validated this session.
