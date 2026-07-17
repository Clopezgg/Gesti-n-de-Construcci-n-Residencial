#!/usr/bin/env bash
set -euo pipefail

run_backup() {
  echo "[$(date -Is)] Starting ConstruControl backup."
  bash /home/frappe/frappe-bench/apps/erpnext/deploy/coolify/backup-now.sh
  echo "[$(date -Is)] ConstruControl backup completed."
}

if [[ "${BACKUP_RUN_ON_START:-true}" == "true" ]]; then
  run_backup
fi

while true; do
  sleep_seconds="$(python3 - <<'PY'
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

zone = ZoneInfo(os.environ.get("TZ", "America/Tegucigalpa"))
hour = int(os.environ.get("BACKUP_LOCAL_HOUR", "2"))
now = datetime.now(zone)
next_run = now.replace(hour=hour, minute=0, second=0, microsecond=0)
if next_run <= now:
    next_run += timedelta(days=1)
print(max(60, int((next_run - now).total_seconds())))
PY
)"
  echo "[$(date -Is)] Next backup in ${sleep_seconds} seconds."
  sleep "$sleep_seconds"
  run_backup
done
