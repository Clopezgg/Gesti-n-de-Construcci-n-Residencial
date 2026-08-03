#!/usr/bin/env bash
set -euo pipefail

QUEUE_FILE="ops/agents/queue/mission_queue.json"
REPORT="ops/agents/reports/dispatch_next.md"
STATE="ops/agents/state/dispatch.env"

mkdir -p ops/agents/reports ops/agents/state

python - <<'PY'
import json
from pathlib import Path
from datetime import datetime

queue_file = Path("ops/agents/queue/mission_queue.json")
report_file = Path("ops/agents/reports/dispatch_next.md")
state_file = Path("ops/agents/state/dispatch.env")

data = json.loads(queue_file.read_text(encoding="utf-8"))
missions = data.get("missions", [])

selected = None
for m in missions:
    if m.get("status") == "queued":
        m["status"] = "running"
        m["dispatched_at"] = datetime.now().isoformat()
        selected = m
        break

queue_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

lines = ["# Dispatch Next", ""]
if selected:
    lines += [
        "## Selected mission",
        f"- target: {selected.get('target','')}",
        f"- domain: {selected.get('domain','')}",
        f"- agent: {selected.get('agent','')}",
        f"- status: {selected.get('status','')}",
        f"- dispatched_at: {selected.get('dispatched_at','')}",
        ""
    ]
    state_file.write_text(
        f"target={selected.get('target','')}\n"
        f"domain={selected.get('domain','')}\n"
        f"agent={selected.get('agent','')}\n"
        f"status={selected.get('status','')}\n",
        encoding="utf-8"
    )
else:
    lines += ["## Selected mission", "No hay misiones en estado queued.", ""]
    state_file.write_text("status=idle\n", encoding="utf-8")

report_file.write_text("\n".join(lines), encoding="utf-8")
PY

echo "Dispatch ejecutado. Revisa $REPORT"
