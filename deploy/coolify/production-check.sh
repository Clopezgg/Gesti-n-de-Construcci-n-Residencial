#!/usr/bin/env bash
set -euo pipefail

cd /home/frappe/frappe-bench

: "${SITE_NAME:?SITE_NAME is required}"
: "${DB_HOST:=mariadb}"
: "${DB_PORT:=3306}"

REQUIRE_MIGRATION="${REQUIRE_MIGRATION:-true}"
REQUIRE_NO_DEMO="${REQUIRE_NO_DEMO:-true}"

case "$REQUIRE_MIGRATION" in true|false) ;; *) echo "REQUIRE_MIGRATION must be true or false" >&2; exit 2;; esac
case "$REQUIRE_NO_DEMO" in true|false) ;; *) echo "REQUIRE_NO_DEMO must be true or false" >&2; exit 2;; esac

echo "=================================================="
echo "CONSTRUCONTROL PRODUCTION CHECK"
echo "Site: $SITE_NAME"
echo "=================================================="

echo "[1/6] Resolving and connecting to private services..."
python3 - "$DB_HOST" "$DB_PORT" <<'PY'
import socket
import sys

checks = [
    (sys.argv[1], int(sys.argv[2]), "MariaDB"),
    ("redis-cache", 6379, "Redis cache"),
    ("redis-queue", 6379, "Redis queue"),
    ("websocket", 9000, "WebSocket"),
]
for host, port, label in checks:
    with socket.create_connection((host, port), timeout=10):
        print(f"OK {label}: {host}:{port}")
PY

echo "[2/6] Checking local Frappe health endpoint..."
python3 - "$SITE_NAME" <<'PY'
import sys
import urllib.request

request = urllib.request.Request(
    "http://127.0.0.1:8000/api/method/ping",
    headers={"Host": sys.argv[1]},
)
with urllib.request.urlopen(request, timeout=15) as response:
    body = response.read().decode("utf-8", errors="replace")
    if response.status != 200 or "message" not in body:
        raise SystemExit(f"Unexpected health response: {response.status} {body[:300]}")
    print(f"OK backend ping: HTTP {response.status}")
PY

echo "[3/6] Running Bench doctor..."
bench --site "$SITE_NAME" doctor

echo "[4/6] Running read-only ConstruControl database checks..."
SMOKE_JSON="$(bench --site "$SITE_NAME" execute erpnext.construcontrol.smoke.run --kwargs "{\"require_migration\":${REQUIRE_MIGRATION},\"require_no_demo\":${REQUIRE_NO_DEMO}}")"
printf '%s\n' "$SMOKE_JSON"
python3 - "$SMOKE_JSON" <<'PY'
import ast
import json
import sys

raw = sys.argv[1].strip()
try:
    result = json.loads(raw)
except json.JSONDecodeError:
    result = ast.literal_eval(raw)
if not result.get("ok"):
    print("ConstruControl smoke test failed:", file=sys.stderr)
    for error in result.get("errors", []):
        print(f"- {error}", file=sys.stderr)
    raise SystemExit(1)
print("OK ConstruControl smoke test")
for warning in result.get("warnings", []):
    print(f"WARNING: {warning}")
PY

echo "[5/6] Verifying a persistent backup exists..."
BACKUP_DIR="sites/${SITE_NAME}/private/backups"
LATEST_BACKUP="$(find "$BACKUP_DIR" -maxdepth 1 -type f -size +0c -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n 1 | cut -d' ' -f2-)"
if [[ -z "$LATEST_BACKUP" ]]; then
    echo "No non-empty backup exists in $BACKUP_DIR" >&2
    exit 1
fi
sha256sum "$LATEST_BACKUP"

echo "[6/6] Checking scheduler state and installed applications..."
bench --site "$SITE_NAME" list-apps
bench --site "$SITE_NAME" show-config | python3 -c 'import json,sys; data=json.load(sys.stdin); print("scheduler_disabled=", data.get("pause_scheduler") or data.get("disable_scheduler") or 0)'

echo "=================================================="
echo "PRODUCTION CHECK COMPLETED SUCCESSFULLY"
echo "=================================================="
