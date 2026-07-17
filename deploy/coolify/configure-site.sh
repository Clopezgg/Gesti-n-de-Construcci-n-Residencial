#!/usr/bin/env bash
set -euo pipefail

mode="${1:-site}"
bench_root="/home/frappe/frappe-bench"
cd "$bench_root"

required=(SITE_NAME DB_HOST DB_PORT DB_NAME DB_PASSWORD REDIS_CACHE REDIS_QUEUE FRAPPE_ENCRYPTION_KEY)
for variable in "${required[@]}"; do
  if [[ -z "${!variable:-}" ]]; then
    echo "Required runtime variable is missing: ${variable}" >&2
    exit 1
  fi
done

mkdir -p sites logs
ls -1 apps > sites/apps.txt

python3 - "$mode" <<'PY'
import json
import os
import pathlib
import sys

mode = sys.argv[1]
sites = pathlib.Path("sites")
common_path = sites / "common_site_config.json"
common = {
    "db_host": os.environ["DB_HOST"],
    "db_port": int(os.environ["DB_PORT"]),
    "redis_cache": os.environ["REDIS_CACHE"],
    "redis_queue": os.environ["REDIS_QUEUE"],
    "redis_socketio": os.environ["REDIS_QUEUE"],
    "socketio_port": int(os.environ.get("SOCKETIO_PORT", "9000")),
    "serve_default_site": True,
    "developer_mode": 0,
}
external_url = os.environ.get("FRAPPE_EXTERNAL_URL", "").rstrip("/")
if external_url:
    common["host_name"] = external_url
common_path.write_text(json.dumps(common, indent=2, sort_keys=True) + "\n", encoding="utf-8")

if mode == "site":
    site_path = sites / os.environ["SITE_NAME"]
    (site_path / "public" / "files").mkdir(parents=True, exist_ok=True)
    (site_path / "private" / "files").mkdir(parents=True, exist_ok=True)
    (site_path / "private" / "backups").mkdir(parents=True, exist_ok=True)
    config = {
        "db_type": "mariadb",
        "db_name": os.environ["DB_NAME"],
        "db_password": os.environ["DB_PASSWORD"],
        "db_host": os.environ["DB_HOST"],
        "db_port": int(os.environ["DB_PORT"]),
        "encryption_key": os.environ["FRAPPE_ENCRYPTION_KEY"],
    }
    config_path = site_path / "site_config.json"
    config_path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    config_path.chmod(0o600)
PY
