#!/usr/bin/env bash
set -euo pipefail

client="$(command -v mariadb || command -v mysql || true)"
if [[ -z "$client" ]]; then
  echo "MariaDB client is unavailable in the application image." >&2
  exit 1
fi

for attempt in $(seq 1 120); do
  if MYSQL_PWD="$DB_PASSWORD" "$client" --protocol=TCP --host="$DB_HOST" --port="$DB_PORT" \
    --user="$DB_NAME" "$DB_NAME" --batch --skip-column-names \
    --execute="SELECT name FROM tabDocType WHERE name='DocType' LIMIT 1" >/dev/null 2>&1; then
    exit 0
  fi
  if [[ "$attempt" == "120" ]]; then
    echo "The ERPNext site schema was not ready after 240 seconds." >&2
    exit 1
  fi
  sleep 2
done
