#!/usr/bin/env bash
set -euo pipefail

COMMAND="${1:-bootstrap}"
REPO_DIR="${NEXORA_REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
BENCH_DIR="${NEXORA_BENCH_DIR:-$HOME/frappe-bench}"
SITE="${NEXORA_SITE:-test_site}"
APP_LINK="$BENCH_DIR/apps/nexora"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_staging_site() {
  case "$SITE" in
    *staging*|*test*|*.localhost|localhost) ;;
    *) fail "El sitio '$SITE' no parece staging/test/local. Defina NEXORA_SITE con un nombre seguro." ;;
  esac
}

require_checkout() {
  test -f "$REPO_DIR/nexora_app/pyproject.toml" || fail "No se encontró nexora_app en $REPO_DIR"
  test -f "$REPO_DIR/scripts/register_nexora_app.py" || fail "Checkout NEXORA incompleto"
}

ensure_bench() {
  if test -x "$BENCH_DIR/env/bin/python" && test -x "$BENCH_DIR/env/bin/pip"; then
    return
  fi
  test -x "$REPO_DIR/.github/helper/install.sh" || fail "No existe un bench y falta .github/helper/install.sh"
  export DB="${DB:-mariadb}"
  export TYPE="${TYPE:-server}"
  export FRAPPE_USER="${FRAPPE_USER:-frappe}"
  export FRAPPE_BRANCH="${FRAPPE_BRANCH:-version-15}"
  export PAYMENTS_BRANCH="${PAYMENTS_BRANCH:-version-15}"
  bash "$REPO_DIR/.github/helper/install.sh"
  test -x "$BENCH_DIR/env/bin/python" || fail "La creación del bench no produjo $BENCH_DIR"
}

link_app() {
  mkdir -p "$BENCH_DIR/apps"
  if test -L "$APP_LINK"; then
    test "$(readlink -f "$APP_LINK")" = "$(readlink -f "$REPO_DIR/nexora_app")" \
      || fail "$APP_LINK apunta a otro checkout"
  elif test -e "$APP_LINK"; then
    fail "$APP_LINK ya existe y no es un enlace simbólico"
  else
    ln -s "$REPO_DIR/nexora_app" "$APP_LINK"
  fi
  "$BENCH_DIR/env/bin/pip" install -e "$APP_LINK"
  python "$REPO_DIR/scripts/register_nexora_app.py" "$BENCH_DIR/sites/apps.txt"
}

site_has_app() {
  cd "$BENCH_DIR"
  bench --site "$SITE" list-apps | awk 'NF {print $1}' | grep -qx "$1"
}

bootstrap() {
  require_staging_site
  require_checkout
  ensure_bench
  link_app
  cd "$BENCH_DIR"
  site_has_app erpnext || fail "El sitio $SITE no tiene ERPNext instalado"
  if ! site_has_app nexora; then
    bench --site "$SITE" install-app nexora
  fi
  bench --site "$SITE" migrate
  bench --site "$SITE" set-config nexora_staging 1
  if test -n "${NEXORA_ADMIN_PASSWORD:-}"; then
    bench --site "$SITE" set-admin-password "$NEXORA_ADMIN_PASSWORD"
  fi
  bench build --app nexora
  bench --site "$SITE" execute nexora.staging.seed_demo_data
  bench --site "$SITE" execute nexora.staging.assert_staging_health
  printf '\nNEXORA 0.1 preparada en el sitio %s.\n' "$SITE"
  printf 'Inicie el servidor con: NEXORA_SITE=%q NEXORA_BENCH_DIR=%q %q serve\n' \
    "$SITE" "$BENCH_DIR" "$0"
}

verify() {
  require_staging_site
  require_checkout
  test -x "$BENCH_DIR/env/bin/python" || fail "Bench no encontrado en $BENCH_DIR"
  cd "$REPO_DIR"
  python scripts/validate_nexora_governance.py \
    --expected-main-head 73c9dadfb81f543e53f45887448fdecbee081850
  python scripts/validate_nexora_app.py
  python scripts/validate_nexora_financial_models.py
  python -m unittest discover -s nexora_app/nexora/tests -p 'test_*contract.py' -v
  PYTHONPATH=nexora_app python -m unittest \
    nexora.tests.test_financial_core \
    nexora.tests.test_ledger_core \
    nexora.tests.test_reference_rules -v
  node --check nexora_app/nexora/nexora/page/nexora_finance/nexora_finance.js
  python -m compileall -q nexora_app/nexora scripts
  cd "$BENCH_DIR"
  bench --site "$SITE" migrate
  bench --site "$SITE" run-tests --app nexora --module nexora.tests.test_installation
  bench --site "$SITE" run-tests --app nexora --module nexora.tests.test_financial_integration
  bench --site "$SITE" run-tests --app nexora --module nexora.tests.test_ledger_integration
  bench --site "$SITE" execute nexora.tests.concurrency_probe.run
  bench --site "$SITE" execute nexora.staging.assert_staging_health
  printf 'NEXORA app y NEXORA financial invariants aprobadas en %s.\n' "$SITE"
}

serve() {
  require_staging_site
  test -d "$BENCH_DIR" || fail "Bench no encontrado en $BENCH_DIR"
  cd "$BENCH_DIR"
  exec bench start
}

case "$COMMAND" in
  bootstrap) bootstrap ;;
  verify) verify ;;
  serve) serve ;;
  *) fail "Comando desconocido '$COMMAND'. Use bootstrap, verify o serve." ;;
esac
