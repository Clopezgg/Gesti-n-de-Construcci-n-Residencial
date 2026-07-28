#!/usr/bin/env bash
set -uo pipefail

wait_for_backend() {
  local endpoint="${FRAPPE_INTERNAL_URL:-http://backend:8000}/api/method/ping"

  for attempt in $(seq 1 300); do
    if python3 - "$endpoint" "$SITE_NAME" <<'PY'
import sys
import urllib.request

endpoint, site = sys.argv[1:3]
request = urllib.request.Request(endpoint, headers={"Host": site})
try:
    with urllib.request.urlopen(request, timeout=5) as response:
        if response.status == 200:
            raise SystemExit(0)
except Exception:
    pass
raise SystemExit(1)
PY
    then
      return 0
    fi

    if [[ "$attempt" == "300" ]]; then
      echo "[$(date -Is)] NEXORA backend did not become ready after 600 seconds." >&2
      return 1
    fi
    sleep 2
  done
}

run_backup() {
  echo "[$(date -Is)] Starting NEXORA backup."
  if bash /home/frappe/frappe-bench/apps/erpnext/deploy/nexora/backup-now.sh; then
    echo "[$(date -Is)] NEXORA backup completed."
    return 0
  fi
  local status=$?
  echo "[$(date -Is)] NEXORA backup failed with exit code ${status}; keeping service running." >&2
  return "$status"
}

if [[ "${BACKUP_RUN_ON_START:-false}" == "true" ]]; then
  if wait_for_backend; then
    run_backup || true
  else
    echo "[$(date -Is)] Initial backup skipped because the backend did not become ready." >&2
  fi
fi

while true; do
  if ! sleep_seconds="$(python3 - <<'PY'
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

zone = ZoneInfo(os.environ.get("TZ", "America/Tegucigalpa"))
hour = int(os.environ.get("BACKUP_LOCAL_HOUR", "2"))
if hour < 0 or hour > 23:
    raise ValueError("BACKUP_LOCAL_HOUR must be between 0 and 23")

now = datetime.now(zone)
next_run = now.replace(hour=hour, minute=0, second=0, microsecond=0)
if next_run <= now:
    next_run += timedelta(days=1)

print(max(60, int((next_run - now).total_seconds())))
PY
  )"; then
    echo "[$(date -Is)] Could not calculate next backup time; retrying in one hour." >&2
    sleep 3600
    continue
  fi

  if [[ ! "$sleep_seconds" =~ ^[0-9]+$ ]]; then
    echo "[$(date -Is)] Invalid backup delay '${sleep_seconds}'; retrying in one hour." >&2
    sleep 3600
    continue
  fi

  echo "[$(date -Is)] Next backup in ${sleep_seconds} seconds."
  sleep "$sleep_seconds"
  run_backup || true
done
