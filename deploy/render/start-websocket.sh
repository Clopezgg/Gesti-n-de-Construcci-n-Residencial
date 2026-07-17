#!/usr/bin/env bash
set -euo pipefail
cd /home/frappe/frappe-bench
export SOCKETIO_PORT="${PORT:-9000}"
bash apps/erpnext/deploy/render/configure-site.sh site
bash apps/erpnext/deploy/render/wait-for-site.sh
exec node apps/frappe/socketio.js
