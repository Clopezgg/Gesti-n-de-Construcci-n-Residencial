#!/usr/bin/env bash
set -Eeuo pipefail

on_error() {
  local status=$?
  echo "[NEXORA] init-site failed: status=$status line=${BASH_LINENO[0]}" >&2
  exit "$status"
}
trap on_error ERR

cd /home/frappe/frappe-bench

ensure_nexora_registered() {
  if [[ ! -d apps/nexora ]]; then
    echo "NEXORA app source is missing at apps/nexora." >&2
    exit 1
  fi
  if ! grep -qx 'nexora' sites/apps.txt 2>/dev/null; then
    printf 'nexora\n' >> sites/apps.txt
  fi
}

wait_for_mariadb() {
  local client
  client="$(command -v mariadb || command -v mysql || true)"
  if [[ -z "$client" ]]; then
    echo "MariaDB client is unavailable in the application image." >&2
    exit 1
  fi

  for attempt in $(seq 1 90); do
    if MYSQL_PWD="$DB_ROOT_PASSWORD" "$client" --protocol=TCP --host="$DB_HOST" --port="$DB_PORT" \
      --user="${DB_ROOT_USER:-root}" --execute="SELECT 1" >/dev/null 2>&1; then
      return 0
    fi
    if [[ "$attempt" == "90" ]]; then
      echo "MariaDB did not become ready after 180 seconds." >&2
      exit 1
    fi
    sleep 2
  done
}

required=(SITE_NAME DB_NAME DB_PASSWORD DB_ROOT_PASSWORD ADMIN_PASSWORD)
for variable in "${required[@]}"; do
  if [[ -z "${!variable:-}" ]]; then
    echo "Required initialization variable is missing: ${variable}" >&2
    exit 1
  fi
done

bash apps/erpnext/deploy/nexora/configure-site.sh common
wait_for_mariadb
ensure_nexora_registered

initialized=0
client="$(command -v mariadb || command -v mysql)"
if MYSQL_PWD="$DB_ROOT_PASSWORD" "$client" --protocol=TCP --host="$DB_HOST" --port="$DB_PORT" \
  --user="${DB_ROOT_USER:-root}" "$DB_NAME" --batch --skip-column-names \
  --execute="SELECT name FROM tabDocType WHERE name='DocType' LIMIT 1" >/dev/null 2>&1; then
  initialized=1
fi

if [[ "$initialized" == "1" ]]; then
  echo "[NEXORA] existing database detected, preserving current data."
  bash apps/erpnext/deploy/nexora/configure-site.sh site
  if ! bench --site "$SITE_NAME" list-apps | grep -qx 'nexora'; then
    echo "[NEXORA] installing app nexora on existing site."
    bench --site "$SITE_NAME" install-app nexora
  fi
  bench --site "$SITE_NAME" migrate
  bench --site "$SITE_NAME" clear-cache
else
  if [[ -e "sites/$SITE_NAME/site_config.json" ]]; then
    echo "Site configuration exists but the database is empty. Refusing to overwrite existing data." >&2
    exit 1
  fi

  echo "[NEXORA] creating site from empty database."
  bench new-site "$SITE_NAME" \
    --db-type mariadb \
    --db-host "$DB_HOST" \
    --db-port="$DB_PORT" \
    --db-name "$DB_NAME" \
    --db-password "$DB_PASSWORD" \
    --db-root-username "${DB_ROOT_USER:-root}" \
    --db-root-password "$DB_ROOT_PASSWORD" \
    --admin-password "$ADMIN_PASSWORD" \
    --mariadb-user-host-login-scope='%' \
    --set-default
  bench --site "$SITE_NAME" install-app erpnext
  bench --site "$SITE_NAME" install-app nexora
  bench --site "$SITE_NAME" migrate
  bench build --app nexora
fi

if [[ "${NEXORA_ENVIRONMENT:-production}" == "staging" ]]; then
  bench --site "$SITE_NAME" set-config nexora_staging 1
  bench --site "$SITE_NAME" execute nexora.financial.staging_setup.ensure_demo_company
fi

bench use "$SITE_NAME"
bench --site "$SITE_NAME" enable-scheduler
bench --site "$SITE_NAME" clear-cache
bench --site "$SITE_NAME" list-apps
