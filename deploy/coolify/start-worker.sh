#!/usr/bin/env bash
set -euo pipefail
queues="${1:-short,default}"
cd /home/frappe/frappe-bench
bash apps/erpnext/deploy/coolify/configure-site.sh common
bash apps/erpnext/deploy/coolify/wait-for-site.sh
exec bench worker --queue "$queues"
