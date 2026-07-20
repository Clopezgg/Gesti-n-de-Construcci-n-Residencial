#!/usr/bin/env bash
set -Eeuo pipefail

on_error() {
  local status=$?
  echo "[ConstruControl] backup failed: status=${status} line=${BASH_LINENO[0]}" >&2
  exit "$status"
}
trap on_error ERR

cd /home/frappe/frappe-bench
bash apps/erpnext/deploy/coolify/configure-site.sh site
bash apps/erpnext/deploy/coolify/wait-for-site.sh

started_at="$(python3 -c 'import time; print(time.time())')"
backup_directory="sites/${SITE_NAME}/private/backups"
archive_directory="sites/${SITE_NAME}/private/backup-archive"
mkdir -p "$backup_directory" "$archive_directory"

bench --site "$SITE_NAME" backup --with-files

archive_result="$(
  python3 apps/erpnext/scripts/archive_backup_set.py \
    --directory "$backup_directory" \
    --destination "$archive_directory" \
    --newer-than "$started_at" \
    --site "$SITE_NAME" \
    --retention-days "${BACKUP_RETENTION_DAYS:-14}"
)"
printf '%s\n' "$archive_result"

manifest="$(
  python3 -c 'import json,sys; print(json.load(sys.stdin)["manifest"])' <<<"$archive_result"
)"
verification="${manifest%/*}/verification.json"
python3 apps/erpnext/scripts/verify_backup_manifest.py \
  --manifest "$manifest" \
  --output "$verification"

printf '%s\n' "$manifest" > "sites/${SITE_NAME}/private/backup-archive/latest-manifest-path"
date -u +%FT%TZ > "sites/${SITE_NAME}/private/backup-archive/last-success-utc"
echo "[ConstruControl] verified backup manifest: ${manifest}"
