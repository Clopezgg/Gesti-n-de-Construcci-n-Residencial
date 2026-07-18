#!/usr/bin/env bash
set -Eeuo pipefail

cd /home/frappe/frappe-bench

LOG_DIR="/home/frappe/frappe-bench/logs"
STARTUP_LOG="$LOG_DIR/construcontrol-backend-startup.log"
mkdir -p "$LOG_DIR"
touch "$STARTUP_LOG"

# Keep startup and migration output in the persistent Docker logs volume so the
# real traceback remains available even when Coolify removes a failed container.
exec > >(tee -a "$STARTUP_LOG") 2>&1

on_error() {
  local status=$?
  echo "[ConstruControl] backend startup failed: status=$status line=${BASH_LINENO[0]} command=${BASH_COMMAND}"
  exit "$status"
}
trap on_error ERR

echo "[ConstruControl] backend startup begin: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "[ConstruControl] site=${SITE_NAME:-unset} db_host=${DB_HOST:-unset} db_name=${DB_NAME:-unset}"

bash apps/erpnext/deploy/coolify/init-site.sh

echo "[ConstruControl] init-site completed; starting gunicorn"
exec /home/frappe/frappe-bench/env/bin/gunicorn --chdir=sites --bind="0.0.0.0:8000" --workers="${GUNICORN_WORKERS:-2}" \
  --threads="${GUNICORN_THREADS:-4}" --worker-class=gthread --worker-tmp-dir=/dev/shm \
  --timeout="${GUNICORN_TIMEOUT:-120}" --preload frappe.app:application