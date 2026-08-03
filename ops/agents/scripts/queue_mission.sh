#!/usr/bin/env bash
set -euo pipefail

MISSION_FILE="ops/agents/missions/current_mission.md"
QUEUE_FILE="ops/agents/queue/mission_queue.json"
REPORT="ops/agents/reports/mission_queue.md"

mkdir -p ops/agents/reports ops/agents/queue

if [ ! -f "$MISSION_FILE" ]; then
  echo "No existe $MISSION_FILE"
  exit 1
fi

domain="$(grep '^Domain:' "$MISSION_FILE" | head -n1 | cut -d':' -f2- | xargs || echo workflow-governance)"
agent="$(grep '^Primary agent:' "$MISSION_FILE" | head -n1 | cut -d':' -f2- | xargs || echo repo-governance)"
target="$(grep '^Mission target:' "$MISSION_FILE" | head -n1 | cut -d':' -f2- | xargs || echo default-mission)"
timestamp="$(date -Iseconds)"

python - <<'PY'
import json, os, re
queue_file = "ops/agents/queue/mission_queue.json"
mission_file = "ops/agents/missions/current_mission.md"

with open(queue_file, "r", encoding="utf-8") as f:
    data = json.load(f)

with open(mission_file, "r", encoding="utf-8") as f:
    text = f.read()

def extract(label, default):
    m = re.search(rf"^{re.escape(label)}:\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else default

item = {
    "timestamp": os.popen("date -Iseconds").read().strip(),
    "target": extract("Mission target", "default-mission"),
    "domain": extract("Domain", "workflow-governance"),
    "agent": extract("Primary agent", "repo-governance"),
    "status": "queued"
}

data.setdefault("missions", []).append(item)

with open(queue_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
PY

{
  echo "# Mission Queue"
  echo
  echo "Fecha: $timestamp"
  echo
  echo "## Última misión encolada"
  echo "- target: $target"
  echo "- domain: $domain"
  echo "- agent: $agent"
  echo "- status: queued"
  echo
  echo "## Queue file"
  echo "- $QUEUE_FILE"
} > "$REPORT"

echo "Misión encolada en $QUEUE_FILE"
echo "Reporte generado en $REPORT"
