#!/usr/bin/env bash
set -euo pipefail

cd /home/frappe/frappe-bench
bash apps/erpnext/deploy/render/configure-site.sh site
bash apps/erpnext/deploy/render/wait-for-site.sh

started_at="$(python3 -c 'import time; print(time.time())')"
backup_directory="sites/${SITE_NAME}/private/backups"
mkdir -p "$backup_directory"

bench --site "$SITE_NAME" backup --with-files
python3 apps/erpnext/scripts/upload_backup_set.py \
	--directory "$backup_directory" \
	--newer-than "$started_at" \
	--bucket "${SUPABASE_BACKUP_BUCKET:-construcontrol-backups}" \
	--site "$SITE_NAME" \
	--delete-local
