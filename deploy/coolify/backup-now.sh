#!/usr/bin/env bash
set -euo pipefail

cd /home/frappe/frappe-bench
bash apps/erpnext/deploy/coolify/configure-site.sh site
bash apps/erpnext/deploy/coolify/wait-for-site.sh

started_at="$(python3 -c 'import time; print(time.time())')"
backup_directory="sites/${SITE_NAME}/private/backups"
archive_directory="sites/${SITE_NAME}/private/backup-archive"
mkdir -p "$backup_directory" "$archive_directory"

bench --site "$SITE_NAME" backup --with-files
python3 apps/erpnext/scripts/archive_backup_set.py \
  --directory "$backup_directory" \
  --destination "$archive_directory" \
  --newer-than "$started_at" \
  --site "$SITE_NAME" \
  --retention-days "${BACKUP_RETENTION_DAYS:-14}"

if [[ -n "${SUPABASE_URL:-}" && -n "${SUPABASE_SERVER_KEY:-}" ]]; then
  echo "Supabase credentials detected. Uploading an additional encrypted-transport copy to the private backup bucket."
  python3 apps/erpnext/scripts/upload_backup_set.py \
    --directory "$backup_directory" \
    --newer-than "$started_at" \
    --bucket "${SUPABASE_BACKUP_BUCKET:-construcontrol-backups}" \
    --site "$SITE_NAME"
else
  echo "No Supabase server credentials were configured. The backup remains in the persistent sites volume."
fi
