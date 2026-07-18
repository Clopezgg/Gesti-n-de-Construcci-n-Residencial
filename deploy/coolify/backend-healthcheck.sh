#!/usr/bin/env bash
set -u

LOG_DIR="/home/frappe/frappe-bench/logs"
HEALTH_LOG="$LOG_DIR/construcontrol-backend-healthcheck.log"
mkdir -p "$LOG_DIR"

output="$({
  python3 - <<'PY'
import os
import urllib.request

site = os.environ.get("SITE_NAME", "construcontrol")
request = urllib.request.Request(
    "http://127.0.0.1:8000/api/method/ping",
    headers={"Host": site},
)
with urllib.request.urlopen(request, timeout=5) as response:
    body = response.read()
    if response.status != 200:
        raise RuntimeError(f"unexpected HTTP status {response.status}: {body[:500]!r}")
PY
} 2>&1)"
status=$?

if [[ "$status" -eq 0 ]]; then
  exit 0
fi

{
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] backend healthcheck failed: status=$status site=${SITE_NAME:-unset}"
  printf '%s\n' "$output"
  echo "---"
} >> "$HEALTH_LOG"

printf '%s\n' "$output" >&2
exit "$status"