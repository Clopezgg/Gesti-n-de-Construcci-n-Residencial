#!/usr/bin/env bash
set -Eeuo pipefail

on_error() {
  local status=$?
  echo "[ConstruControl] init-site failed: status=$status line=${BASH_LINENO[0]}"
  exit "$status"
}
trap on_error ERR

cd /home/frappe/frappe-bench

echo "[ConstruControl] step configure-common start"
bash apps/erpnext/deploy/coolify/configure-site.sh common
echo "[ConstruControl] step configure-common ok"

required=(ADMIN_PASSWORD DB_ROOT_USER DB_ROOT_PASSWORD)
for variable in "${required[@]}"; do
  if [[ -z "${!variable:-}" ]]; then
    echo "Required initialization variable is missing: ${variable}" >&2
    exit 1
  fi
done

client="$(command -v mariadb || command -v mysql || true)"
if [[ -z "$client" ]]; then
  echo "MariaDB client is unavailable in the application image." >&2
  exit 1
fi

echo "[ConstruControl] step database-ready start"
for attempt in $(seq 1 90); do
  if MYSQL_PWD="$DB_ROOT_PASSWORD" "$client" --protocol=TCP --host="$DB_HOST" --port="$DB_PORT" \
    --user="$DB_ROOT_USER" --execute="SELECT 1" >/dev/null 2>&1; then
    break
  fi
  if [[ "$attempt" == "90" ]]; then
    echo "MariaDB did not become ready after 180 seconds." >&2
    exit 1
  fi
  sleep 2
done
echo "[ConstruControl] step database-ready ok"

initialized=0
if MYSQL_PWD="$DB_ROOT_PASSWORD" "$client" --protocol=TCP --host="$DB_HOST" --port="$DB_PORT" \
  --user="$DB_ROOT_USER" "$DB_NAME" --batch --skip-column-names \
  --execute="SELECT name FROM tabDocType WHERE name='DocType' LIMIT 1" >/dev/null 2>&1; then
  initialized=1
fi

if [[ "$initialized" == "1" ]]; then
  echo "Existing ERPNext database detected. Running migrations."
  echo "[ConstruControl] step configure-site start"
  bash apps/erpnext/deploy/coolify/configure-site.sh site
  echo "[ConstruControl] step configure-site ok"
  echo "[ConstruControl] step bench-migrate start"
  bench --site "$SITE_NAME" migrate
  echo "[ConstruControl] step bench-migrate ok"
else
  if [[ -e "sites/$SITE_NAME/site_config.json" ]]; then
    echo "A site configuration exists but the database is empty. Refusing to overwrite it automatically." >&2
    echo "Restore the database or remove the stale site volume only after confirming that no data must be preserved." >&2
    exit 1
  fi
  echo "Creating the ERPNext site for the first time."
  echo "[ConstruControl] step new-site start"
  bench new-site "$SITE_NAME" \
    --db-type mariadb \
    --db-host "$DB_HOST" \
    --db-port "$DB_PORT" \
    --db-name "$DB_NAME" \
    --db-password "$DB_PASSWORD" \
    --db-root-username "$DB_ROOT_USER" \
    --db-root-password "$DB_ROOT_PASSWORD" \
    --admin-password "$ADMIN_PASSWORD" \
    --mariadb-user-host-login-scope='%' \
    --install-app erpnext \
    --set-default
  echo "[ConstruControl] step new-site ok"
  echo "[ConstruControl] step bench-migrate start"
  bench --site "$SITE_NAME" migrate
  echo "[ConstruControl] step bench-migrate ok"
fi

echo "[ConstruControl] step bench-use start"
bench use "$SITE_NAME"
echo "[ConstruControl] step bench-use ok"

echo "[ConstruControl] step enable-scheduler start"
bench --site "$SITE_NAME" enable-scheduler
echo "[ConstruControl] step enable-scheduler ok"

echo "[ConstruControl] step clear-cache start"
bench --site "$SITE_NAME" clear-cache
echo "[ConstruControl] step clear-cache ok"

echo "[ConstruControl] step list-apps start"
bench --site "$SITE_NAME" list-apps
echo "[ConstruControl] step list-apps ok"