#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage:
  restore-verify.sh MANIFEST_PATH TEST_SITE

Restores a verified backup into an isolated site, runs three migrations,
executes the ConstruControl runtime smoke test, and writes evidence.
The production SITE_NAME is never accepted as TEST_SITE.
EOF
}

if [[ "$#" -ne 2 ]]; then
  usage >&2
  exit 2
fi

manifest="$1"
test_site="$2"
cd /home/frappe/frappe-bench

if [[ -z "${SITE_NAME:-}" || -z "${DB_ROOT_PASSWORD:-}" || -z "${ADMIN_PASSWORD:-}" ]]; then
  echo "SITE_NAME, DB_ROOT_PASSWORD and ADMIN_PASSWORD are required." >&2
  exit 1
fi
if [[ "$test_site" == "$SITE_NAME" ]]; then
  echo "Refusing to restore over the production site." >&2
  exit 1
fi
if [[ ! "$test_site" =~ ^[a-zA-Z0-9][a-zA-Z0-9.-]{2,62}$ ]]; then
  echo "Unsafe test site name: $test_site" >&2
  exit 1
fi

verification="$(mktemp)"
python3 apps/erpnext/scripts/verify_backup_manifest.py \
  --manifest "$manifest" \
  --output "$verification" >/dev/null

readarray -t backup_files < <(
  python3 - "$verification" <<'PY'
import json
import sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
categories = payload["categories"]
for key in ("database", "public_files", "private_files", "site_config"):
    print(categories[key])
PY
)
database_file="${backup_files[0]}"
public_files="${backup_files[1]}"
private_files="${backup_files[2]}"
site_config_file="${backup_files[3]}"

if [[ -d "sites/$test_site" ]]; then
  echo "Test site already exists: $test_site" >&2
  echo "Remove it explicitly only after confirming it is disposable." >&2
  exit 1
fi

evidence_dir="sites/${SITE_NAME}/private/restore-evidence/${test_site}-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$evidence_dir"
cp "$verification" "$evidence_dir/backup-verification.json"
cp "$site_config_file" "$evidence_dir/source-site-config-backup.json"

cleanup_required=0
cleanup() {
  local status=$?
  if [[ "$cleanup_required" == "1" && "${KEEP_RESTORE_TEST_SITE:-false}" != "true" ]]; then
    bench drop-site "$test_site" \
      --db-root-username "${DB_ROOT_USER:-root}" \
      --db-root-password "$DB_ROOT_PASSWORD" \
      --force >/dev/null 2>&1 || true
    bench use "$SITE_NAME" >/dev/null 2>&1 || true
  fi
  rm -f "$verification"
  exit "$status"
}
trap cleanup EXIT

bench new-site "$test_site" \
  --db-type mariadb \
  --db-host "${DB_HOST:-mariadb}" \
  --db-port "${DB_PORT:-3306}" \
  --db-root-username "${DB_ROOT_USER:-root}" \
  --db-root-password "$DB_ROOT_PASSWORD" \
  --admin-password "$ADMIN_PASSWORD" \
  --mariadb-user-host-login-scope='%' \
  --install-app erpnext \
  --set-default
cleanup_required=1

bench --site "$test_site" restore "$database_file" \
  --with-public-files "$public_files" \
  --with-private-files "$private_files" \
  --db-root-username "${DB_ROOT_USER:-root}" \
  --db-root-password "$DB_ROOT_PASSWORD" \
  --force

if [[ -n "${FRAPPE_ENCRYPTION_KEY:-}" ]]; then
  bench --site "$test_site" set-config encryption_key "$FRAPPE_ENCRYPTION_KEY"
fi

for migration in 1 2 3; do
  echo "[ConstruControl] restore migration ${migration}/3"
  bench --site "$test_site" migrate
done
bench --site "$test_site" clear-cache
bench --site "$test_site" enable-scheduler

echo "[ConstruControl] restore runtime smoke start"
runtime_stderr="$(mktemp)"
if ! bench --site "$test_site" execute erpnext.construcontrol.tests.runtime_smoke.run \
  >"$evidence_dir/runtime-smoke.json" 2>"$runtime_stderr"; then
  echo "[ConstruControl] restore runtime smoke failed"
  cat "$runtime_stderr"
  rm -f "$runtime_stderr"
  exit 1
fi
rm -f "$runtime_stderr"
echo "[ConstruControl] restore runtime smoke ok"

echo "[ConstruControl] restore count reconciliation start"
python3 - "$SITE_NAME" "$test_site" "$evidence_dir/reconciliation.json" <<'PY'
import json
import subprocess
import sys

source_site, restored_site, output = sys.argv[1:]
doctypes = [
    "User",
    "Project",
    "CC Funding Source",
    "CC Expense Control",
    "CC Labor Contract",
    "CC Material Ledger",
    "CC Inventory Movement",
    "CC Progress Update",
    "CC Weekly Closing",
    "CC Audit Log",
]


def count(site, doctype):
    command = [
        "bench",
        "--site",
        site,
        "execute",
        "erpnext.construcontrol.migration.restore_verification.count_records",
        "--kwargs",
        json.dumps({"doctype": doctype}, separators=(",", ":")),
    ]
    try:
        completed = subprocess.run(command, text=True, capture_output=True, check=True)
    except subprocess.CalledProcessError as error:
        if error.stdout:
            print(error.stdout, end="")
        if error.stderr:
            print(error.stderr, end="")
        raise
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"No restore count result for {doctype} on {site}")
    payload = json.loads(lines[-1])
    if payload.get("doctype") != doctype:
        raise RuntimeError(f"Unexpected restore count payload for {doctype}: {payload}")
    return int(payload["count"])


source_counts = {doctype: count(source_site, doctype) for doctype in doctypes}
restored_counts = {doctype: count(restored_site, doctype) for doctype in doctypes}
mismatches = {
    doctype: {"source": source_counts[doctype], "restored": restored_counts[doctype]}
    for doctype in doctypes
    if source_counts[doctype] != restored_counts[doctype]
}
payload = {
    "source_site": source_site,
    "restored_site": restored_site,
    "source_counts": source_counts,
    "restored_counts": restored_counts,
    "mismatches": mismatches,
    "status": "reconciled" if not mismatches else "failed",
}
with open(output, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
print(json.dumps(payload, ensure_ascii=False))
if mismatches:
    raise SystemExit("Restore count reconciliation failed")
PY
echo "[ConstruControl] restore count reconciliation ok"

{
  echo "source_site=${SITE_NAME}"
  echo "test_site=${test_site}"
  echo "verified_manifest=${manifest}"
  echo "completed_at=$(date -u +%FT%TZ)"
  echo "migrations=3"
  echo "count_reconciliation=passed"
  echo "status=passed"
} > "$evidence_dir/restore-result.env"

echo "[ConstruControl] isolated restore verified: ${evidence_dir}"
