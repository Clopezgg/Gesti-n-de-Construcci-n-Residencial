#!/usr/bin/env bash
set -Eeuo pipefail

cd /home/frappe/frappe-bench

SOURCE_DIR="apps/nexora/nexora/public"
TARGET_DIR="sites/assets/nexora"
REQUIRED_ASSETS=(
  "css/nexora.css"
  "js/nexora.js"
  "js/nexora_quick_flows.js"
)

for attempt in $(seq 1 120); do
  if [[ -d "$SOURCE_DIR" ]]; then
    ready=1
    for asset in "${REQUIRED_ASSETS[@]}"; do
      if [[ ! -s "$SOURCE_DIR/$asset" ]]; then
        ready=0
        break
      fi
    done
    if [[ "$ready" == "1" ]]; then
      break
    fi
  fi

  if [[ "$attempt" == "120" ]]; then
    echo "NEXORA public assets were not available after 240 seconds." >&2
    exit 1
  fi
  sleep 2
done

mkdir -p sites/assets
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"
cp -a "$SOURCE_DIR"/. "$TARGET_DIR"/

for asset in "${REQUIRED_ASSETS[@]}"; do
  if [[ ! -s "$TARGET_DIR/$asset" ]]; then
    echo "Required NEXORA asset was not published: $TARGET_DIR/$asset" >&2
    exit 1
  fi
done

echo "[NEXORA] frontend assets published into the shared sites volume"
exec nginx-entrypoint.sh
