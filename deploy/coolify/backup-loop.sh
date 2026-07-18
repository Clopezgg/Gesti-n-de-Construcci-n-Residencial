#!/usr/bin/env bash
set -uo pipefail

run_backup() {
  echo "[$(date -Is)] Starting ConstruControl backup."
  if bash /home/frappe/frappe-bench/apps/erpnext/deploy/coolify/backup-now.sh; then
    echo "[$(date -Is)] ConstruControl backup completed."
    return 0
  fi

  status=$?
  echo "[$(date -Is)] ConstruControl backup failed with exit code ${status}; the backup service will remain running." >&2
  return "$status"
}

if [[ "${BACKUP_RUN_ON_START:-false}" == "true" ]]; then
  run_backup || true
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
    echo "[$(date -Is)] Could not calculate the next backup time; retrying in one hour." >&2
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
