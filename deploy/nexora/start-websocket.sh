#!/usr/bin/env bash
set -Eeuo pipefail

cd /home/frappe/frappe-bench
bash apps/erpnext/deploy/nexora/configure-site.sh common

wait_for_backend() {
  local endpoint="${FRAPPE_INTERNAL_URL:-http://backend:8000}/api/method/ping"

  for attempt in $(seq 1 300); do
    if python3 - "$endpoint" "$SITE_NAME" <<'PY'
import sys
import urllib.request

endpoint, site = sys.argv[1:3]
request = urllib.request.Request(endpoint, headers={"Host": site})
try:
    with urllib.request.urlopen(request, timeout=5) as response:
        if response.status == 200:
            raise SystemExit(0)
except Exception:
    pass
raise SystemExit(1)
PY
    then
      echo "[NEXORA] backend ready; starting websocket."
      return 0
    fi

    if [[ "$attempt" == "300" ]]; then
      echo "NEXORA backend did not become ready after 600 seconds; websocket will stop." >&2
      exit 1
    fi
    sleep 2
  done
}

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

wait_for_backend
start_loopback_auth_proxy
exec node apps/frappe/socketio.js
