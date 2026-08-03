#!/usr/bin/env bash
set -euo pipefail

INDEX="${1:-1}"
NEW_STATUS="${2:-blocked}"

QUEUE_FILE="ops/agents/queue/mission_queue.json"
REPORT="ops/agents/reports/update_mission_status.md"

mkdir -p ops/agents/reports

python - <<PY
import json
from pathlib import Path

idx = int("${INDEX}")
new_status = "${NEW_STATUS}"

queue_file = Path("ops/agents/queue/mission_queue.json")
report_file = Path("ops/agents/reports/update_mission_status.md")

data = json.loads(queue_file.read_text(encoding="utf-8"))
missions = data.get("missions", [])

lines = ["# Update Mission Status", ""]
if 1 <= idx <= len(missions):
    old = missions[idx - 1].get("status", "")
    missions[idx - 1]["status"] = new_status
    lines += [
        f"- mission_index: {idx}",
        f"- old_status: {old}",
        f"- new_status: {new_status}"
    ]
else:
    lines += [f"- invalid mission_index: {idx}"]

queue_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
report_file.write_text("\n".join(lines), encoding="utf-8")
PY

echo "Estado actualizado. Revisa $REPORT"
