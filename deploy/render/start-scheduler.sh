#!/usr/bin/env bash
set -euo pipefail
cd /home/frappe/frappe-bench
bash apps/erpnext/deploy/render/configure-site.sh site
bash apps/erpnext/deploy/render/wait-for-site.sh
exec bench schedule
