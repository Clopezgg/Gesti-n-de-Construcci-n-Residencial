#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage:
  restore-verify.sh MANIFEST_PATH TEST_SITE

Restores a verified backup into an isolated site, runs three migrations,
confirms required apps (frappe, erpnext, nexora), and writes evidence.
The production SITE_NAME is never accepted as TEST_SITE.
EOF
}

if [[ "$#" -ne 2 ]]; then
  usage >&2
  exit 2
fi

manifest="$1"
test_site="$2"
cd /home/frappe/frappe-bench

if [[ -z "${SITE_NAME:-}" || -z "${DB_ROOT_PASSWORD:-}" || -z "${ADMIN_PASSWORD:-}" ]]; then
  echo "SITE_NAME, DB_ROOT_PASSWORD and ADMIN_PASSWORD are required." >&2
  exit 1
fi
if [[ "$test_site" == "$SITE_NAME" ]]; then
  echo "Refusing to restore over the production site." >&2
  exit 1
fi
if [[ ! "$test_site" =~ ^[a-zA-Z0-9][a-zA-Z0-9.-]{2,62}$ ]]; then
  echo "Unsafe test site name: $test_site" >&2
  exit 1
fi

verification="$(mktemp)"
python3 apps/erpnext/scripts/verify_backup_manifest.py \
  --manifest "$manifest" \
  --output "$verification" >/dev/null

readarray -t backup_files < <(
  python3 - "$verification" <<'PY'
import json
import sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
categories = payload["categories"]
for key in ("database", "public_files", "private_files", "site_config"):
    print(categories[key])
PY
)
database_file="${backup_files[0]}"
public_files="${backup_files[1]}"
private_files="${backup_files[2]}"
site_config_file="${backup_files[3]}"

if [[ -d "sites/$test_site" ]]; then
  echo "Test site already exists: $test_site" >&2
  exit 1
fi

evidence_dir="sites/${SITE_NAME}/private/restore-evidence/${test_site}-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$evidence_dir"
cp "$verification" "$evidence_dir/backup-verification.json"
cp "$site_config_file" "$evidence_dir/source-site-config-backup.json"

cleanup_required=0
cleanup() {
  local status=$?
  if [[ "$cleanup_required" == "1" && "${KEEP_RESTORE_TEST_SITE:-false}" != "true" ]]; then
    bench drop-site "$test_site" \
      --db-root-username "${DB_ROOT_USER:-root}" \
      --db-root-password "$DB_ROOT_PASSWORD" \
      --force >/dev/null 2>&1 || true
    bench use "$SITE_NAME" >/dev/null 2>&1 || true
  fi
  rm -f "$verification"
  exit "$status"
}
trap cleanup EXIT

bench new-site "$test_site" \
  --db-type mariadb \
  --db-host "${DB_HOST:-mariadb}" \
  --db-port "${DB_PORT:-3306}" \
  --db-root-username "${DB_ROOT_USER:-root}" \
  --db-root-password "$DB_ROOT_PASSWORD" \
  --admin-password "$ADMIN_PASSWORD" \
  --mariadb-user-host-login-scope='%' \
  --set-default
cleanup_required=1

bench --site "$test_site" restore "$database_file" \
  --with-public-files "$public_files" \
  --with-private-files "$private_files" \
  --db-root-username "${DB_ROOT_USER:-root}" \
  --db-root-password "$DB_ROOT_PASSWORD" \
  --force

if [[ -n "${FRAPPE_ENCRYPTION_KEY:-}" ]]; then
  bench --site "$test_site" set-config encryption_key "$FRAPPE_ENCRYPTION_KEY"
fi

for migration in 1 2 3; do
  echo "[NEXORA] restore migration ${migration}/3"
  bench --site "$test_site" migrate
done
bench --site "$test_site" clear-cache
bench --site "$test_site" enable-scheduler

apps_output="$evidence_dir/list-apps.txt"
bench --site "$test_site" list-apps | tee "$apps_output"
for app in frappe erpnext nexora; do
  if ! grep -qx "$app" "$apps_output"; then
    echo "Expected app '$app' was not installed on restored site." >&2
    exit 1
  fi
done

{
  echo "source_site=${SITE_NAME}"
  echo "test_site=${test_site}"
  echo "verified_manifest=${manifest}"
  echo "completed_at=$(date -u +%FT%TZ)"
  echo "migrations=3"
  echo "required_apps=frappe,erpnext,nexora"
  echo "status=passed"
} > "$evidence_dir/restore-result.env"

echo "[NEXORA] isolated restore verified: ${evidence_dir}"
