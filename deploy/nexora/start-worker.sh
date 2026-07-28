#!/usr/bin/env bash
set -Eeuo pipefail

queues="${1:-short,default}"
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
      echo "[NEXORA] backend ready; starting worker queues=${queues}."
      return 0
    fi

    if [[ "$attempt" == "300" ]]; then
      echo "NEXORA backend did not become ready after 600 seconds; worker queues=${queues} will stop." >&2
      exit 1
    fi
    sleep 2
  done
}

wait_for_backend
exec bench worker --queue "$queues"
