#!/usr/bin/env bash
set -euo pipefail
cd /home/frappe/frappe-bench
bash apps/erpnext/deploy/coolify/configure-site.sh common
bash apps/erpnext/deploy/coolify/wait-for-site.sh
exec bench schedule
