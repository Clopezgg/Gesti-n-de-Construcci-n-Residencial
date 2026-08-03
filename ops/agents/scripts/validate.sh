#!/usr/bin/env bash
set -euo pipefail

mkdir -p ops/agents/reports

{
  echo "# Validation Report"
  echo
  echo "## Fecha"
  date -Iseconds
  echo
  echo "## Python version"
  python --version 2>&1 || true
  echo
  echo "## Node version"
  node --version 2>&1 || true
  echo
  echo "## npm version"
  npm --version 2>&1 || true
  echo
  echo "## Pytest collection"
  pytest --collect-only nexora_app/nexora/tests 2>&1 || true
  echo
  echo "## npm test"
  npm test --if-present 2>&1 || true
} > ops/agents/reports/validation.md

echo "Validación generada en ops/agents/reports/validation.md"
