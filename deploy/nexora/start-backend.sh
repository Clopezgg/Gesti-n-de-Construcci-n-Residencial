#!/usr/bin/env bash
set -Eeuo pipefail

cd /home/frappe/frappe-bench

LOG_DIR="/home/frappe/frappe-bench/logs"
STARTUP_LOG="$LOG_DIR/nexora-backend-startup.log"
mkdir -p "$LOG_DIR"
touch "$STARTUP_LOG"

exec > >(tee -a "$STARTUP_LOG") 2>&1

on_error() {
  local status=$?
  echo "[NEXORA] backend startup failed: status=$status line=${BASH_LINENO[0]} command=${BASH_COMMAND}" >&2
  exit "$status"
}
trap on_error ERR

echo "[NEXORA] backend startup begin: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "[NEXORA] site=${SITE_NAME:-unset} db_host=${DB_HOST:-unset} db_name=${DB_NAME:-unset}"

mkdir -p sites/assets
ln -sfn /home/frappe/frappe-bench/apps/nexora/nexora/public sites/assets/nexora

echo "[NEXORA] public assets linked into shared sites volume"
bash apps/erpnext/deploy/nexora/init-site.sh

echo "[NEXORA] init-site completed; starting gunicorn"
exec /home/frappe/frappe-bench/env/bin/gunicorn --chdir=sites --bind="0.0.0.0:8000" --workers="${GUNICORN_WORKERS:-2}" \
  --threads="${GUNICORN_THREADS:-4}" --worker-class=gthread --worker-tmp-dir=/dev/shm \
  --timeout="${GUNICORN_TIMEOUT:-120}" --preload frappe.app:application
