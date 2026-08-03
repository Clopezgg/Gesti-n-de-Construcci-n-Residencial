# Redeploy Watch

Fecha: 2026-08-03T17:01:34+00:00
Target: manual-redeploy

## Git status
 M .github/workflows/nexora-redeploy-watch.yml
 M ops/agents/reports/validation.md
?? auto_merge_ready_prs.sh
?? nexora_mass_cleanup.sh
?? ops/agents/config/redeploy_policy.json
?? ops/agents/reports/redeploy_watch.md
?? ops/agents/reports/regression_scan.md
?? ops/agents/scripts/redeploy_watch.sh
?? ops/agents/scripts/regression_scan.sh
?? pr_audit_report.txt

## Required reports
- OK: ops/agents/reports/guided_review.md
- OK: ops/agents/reports/unified_gate.md
- OK: ops/agents/reports/domain_map.md

## Candidate regression paths
nexora_app/nexora/progress
nexora_app/nexora/notifications
nexora_app/nexora/patches
nexora_app/nexora/public
nexora_app/nexora/page
.github/workflows

## Recent changed files
.github/workflows/nexora-guided-review.yml
docs/architecture/file_inventory.json
ops/agents/config/review_matrix.json
ops/agents/prompts/guided-review.md
ops/agents/reports/domain_map.md
ops/agents/reports/guided_review.md
ops/agents/reports/validation.md
ops/agents/scripts/guided_review.sh
ops/agents/state/guided_review.env

## Verdict
BLOCKED: git status no está limpio.
