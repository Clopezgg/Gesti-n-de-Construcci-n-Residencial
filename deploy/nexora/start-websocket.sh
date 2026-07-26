#!/usr/bin/env bash
set -euo pipefail

cd /home/frappe/frappe-bench
bash apps/erpnext/deploy/nexora/configure-site.sh common

client="$(command -v mariadb || command -v mysql || true)"
if [[ -z "$client" ]]; then
  echo "MariaDB client is unavailable in the application image." >&2
  exit 1
fi

start_loopback_auth_proxy() {
  local external_host
  external_host="$(python3 - <<'PY'
import os
from urllib.parse import urlparse
print(urlparse(os.environ.get("FRAPPE_EXTERNAL_URL", "")).hostname or "")
PY
)"

  if [[ "$external_host" != "127.0.0.1" && "$external_host" != "localhost" ]]; then
    return 0
  fi

  echo "[NEXORA] starting loopback realtime authentication proxy for ${FRAPPE_EXTERNAL_URL}"
  python3 -u - <<'PY' &
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

backend = os.environ.get("FRAPPE_INTERNAL_URL", "http://backend:8000").rstrip("/")
site = os.environ["SITE_NAME"]

class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        headers = {
            "Host": site,
            "X-Frappe-Site-Name": site,
            "X-Forwarded-Proto": "http",
        }
        authorization = self.headers.get("Authorization")
        if authorization:
            headers["Authorization"] = authorization
        cookie = self.headers.get("Cookie")
        if cookie:
            headers["Cookie"] = cookie

        request = Request(f"{backend}{self.path}", headers=headers, method="GET")
        try:
            response = urlopen(request, timeout=15)
            status = response.status
            body = response.read()
            content_type = response.headers.get("Content-Type", "application/json")
        except HTTPError as error:
            status = error.code
            body = error.read()
            content_type = error.headers.get("Content-Type", "application/json")
        except Exception as error:
            status = 502
            body = str(error).encode("utf-8")
            content_type = "text/plain; charset=utf-8"

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return

ThreadingHTTPServer(("127.0.0.1", 8080), ProxyHandler).serve_forever()
PY
}

for attempt in $(seq 1 120); do
  if MYSQL_PWD="$DB_PASSWORD" "$client" --protocol=TCP --host="$DB_HOST" --port="$DB_PORT" \
    --user="$DB_NAME" "$DB_NAME" --batch --skip-column-names \
    --execute="SELECT name FROM tabDocType WHERE name='DocType' LIMIT 1" >/dev/null 2>&1; then
    start_loopback_auth_proxy
    exec node apps/frappe/socketio.js
  fi
  if [[ "$attempt" == "120" ]]; then
    echo "The ERPNext site schema was not ready after 240 seconds." >&2
    exit 1
  fi
  sleep 2
done
