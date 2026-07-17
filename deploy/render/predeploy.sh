#!/usr/bin/env bash
set -euo pipefail

cd /home/frappe/frappe-bench
bash apps/erpnext/deploy/render/configure-site.sh common

required=(ADMIN_PASSWORD DB_ROOT_USER DB_ROOT_PASSWORD)
for variable in "${required[@]}"; do
	if [[ -z "${!variable:-}" ]]; then
		echo "Required pre-deploy variable is missing: ${variable}" >&2
		exit 1
	fi
done

client="$(command -v mariadb || command -v mysql || true)"
if [[ -z "$client" ]]; then
	echo "MariaDB client is unavailable in the runtime image." >&2
	exit 1
fi

initialized=0
if MYSQL_PWD="$DB_ROOT_PASSWORD" "$client" --protocol=TCP --host="$DB_HOST" --port="$DB_PORT" \
	--user="$DB_ROOT_USER" "$DB_NAME" --batch --skip-column-names \
	--execute="SELECT name FROM tabDocType WHERE name='DocType' LIMIT 1" >/dev/null 2>&1; then
	initialized=1
fi

if [[ "$initialized" == "1" ]]; then
	bash apps/erpnext/deploy/render/configure-site.sh site
	bench --site "$SITE_NAME" migrate
else
	if [[ -e "sites/$SITE_NAME/site_config.json" ]]; then
		echo "Refusing first-time initialization because a site config already exists while the database is empty." >&2
		exit 1
	fi
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
	bench --site "$SITE_NAME" migrate
fi

bench --site "$SITE_NAME" list-apps
