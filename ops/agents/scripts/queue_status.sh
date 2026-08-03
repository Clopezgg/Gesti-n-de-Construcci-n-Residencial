#!/usr/bin/env bash
set -euo pipefail

QUEUE_FILE="ops/agents/queue/mission_queue.json"
REPORT="ops/agents/reports/queue_status.md"
mkdir -p ops/agents/reports

python - <<'PY'
import json
from pathlib import Path

queue_file = Path("ops/agents/queue/mission_queue.json")
report_file = Path("ops/agents/reports/queue_status.md")

data = json.loads(queue_file.read_text(encoding="utf-8"))
missions = data.get("missions", [])

lines = []
lines.append("# Queue Status")
lines.append("")
lines.append(f"Total missions: {len(missions)}")
lines.append("")
lines.append("| # | target | domain | agent | status |")
lines.append("|---|---|---|---|---|")
for i, m in enumerate(missions, 1):
    lines.append(f"| {i} | {m.get('target','')} | {m.get('domain','')} | {m.get('agent','')} | {m.get('status','')} |")

report_file.write_text("\n".join(lines), encoding="utf-8")
PY

echo "Estado de cola generado en $REPORT"
