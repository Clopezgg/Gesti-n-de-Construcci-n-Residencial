#!/usr/bin/env bash
set -euo pipefail

export PORT="${PORT:-8080}"
export UPSTREAM_REAL_IP_ADDRESS="${UPSTREAM_REAL_IP_ADDRESS:-0.0.0.0/0}"
export UPSTREAM_REAL_IP_HEADER="${UPSTREAM_REAL_IP_HEADER:-X-Forwarded-For}"
export UPSTREAM_REAL_IP_RECURSIVE="${UPSTREAM_REAL_IP_RECURSIVE:-on}"
export PROXY_READ_TIMEOUT="${PROXY_READ_TIMEOUT:-120}"
export CLIENT_MAX_BODY_SIZE="${CLIENT_MAX_BODY_SIZE:-50m}"

required=(BACKEND SOCKETIO FRAPPE_SITE_NAME_HEADER)
for variable in "${required[@]}"; do
	if [[ -z "${!variable:-}" ]]; then
		echo "Required frontend variable is missing: ${variable}" >&2
		exit 1
	fi
done

envsubst '${PORT} ${BACKEND} ${SOCKETIO} ${UPSTREAM_REAL_IP_ADDRESS} ${UPSTREAM_REAL_IP_HEADER} ${UPSTREAM_REAL_IP_RECURSIVE} ${FRAPPE_SITE_NAME_HEADER} ${PROXY_READ_TIMEOUT} ${CLIENT_MAX_BODY_SIZE}' \
	< /home/frappe/frappe-bench/apps/erpnext/deploy/render/nginx.conf.template \
	> /etc/nginx/conf.d/frappe.conf
exec nginx -g 'daemon off;'
