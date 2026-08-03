#!/usr/bin/env bash
set -euo pipefail

QUEUE_FILE="ops/agents/queue/mission_queue.json"
REPORT="ops/agents/dashboard/mission_dashboard.md"

mkdir -p ops/agents/dashboard

python - <<'PY'
import json
from pathlib import Path
from collections import Counter

queue_file = Path("ops/agents/queue/mission_queue.json")
report_file = Path("ops/agents/dashboard/mission_dashboard.md")

data = json.loads(queue_file.read_text(encoding="utf-8"))
missions = data.get("missions", [])
counts = Counter(m.get("status", "unknown") for m in missions)

lines = []
lines.append("# Mission Dashboard")
lines.append("")
lines.append("## Summary")
lines.append(f"- total: {len(missions)}")
lines.append(f"- queued: {counts.get('queued',0)}")
lines.append(f"- running: {counts.get('running',0)}")
lines.append(f"- blocked: {counts.get('blocked',0)}")
lines.append(f"- done: {counts.get('done',0)}")
lines.append("")
lines.append("## Missions")
lines.append("")
lines.append("| # | target | domain | agent | status |")
lines.append("|---|---|---|---|---|")
for i, m in enumerate(missions, 1):
    lines.append(f"| {i} | {m.get('target','')} | {m.get('domain','')} | {m.get('agent','')} | {m.get('status','')} |")

report_file.write_text("\n".join(lines), encoding="utf-8")
PY

echo "Dashboard generado en $REPORT"
