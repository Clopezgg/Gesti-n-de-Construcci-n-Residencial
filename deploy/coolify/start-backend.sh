#!/usr/bin/env bash
set -euo pipefail
cd /home/frappe/frappe-bench
bash apps/erpnext/deploy/coolify/configure-site.sh site
bash apps/erpnext/deploy/coolify/wait-for-site.sh
exec /home/frappe/frappe-bench/env/bin/gunicorn --chdir=sites --bind="0.0.0.0:8000" --workers="${GUNICORN_WORKERS:-2}" \
  --threads="${GUNICORN_THREADS:-4}" --worker-class=gthread --worker-tmp-dir=/dev/shm \
  --timeout="${GUNICORN_TIMEOUT:-120}" --preload frappe.app:application
