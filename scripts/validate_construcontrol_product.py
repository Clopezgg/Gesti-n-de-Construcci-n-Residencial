#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "erpnext/construcontrol/profile.py",
    "erpnext/construcontrol/finance.py",
    "erpnext/construcontrol/finance_setup.py",
    "erpnext/construcontrol/expenses.py",
    "erpnext/construcontrol/expense_setup.py",
    "erpnext/construcontrol/construction.py",
    "erpnext/construcontrol/construction_setup.py",
    "erpnext/construcontrol/integrations.py",
    "erpnext/construcontrol/integration_setup.py",
    "erpnext/construcontrol/executive.py",
    "erpnext/construcontrol/executive_reports.py",
    "erpnext/construcontrol/page/construcontrol_dashboard/construcontrol_dashboard.js",
    "erpnext/construcontrol/page/construcontrol_profile/construcontrol_profile.js",
    "erpnext/construcontrol/page/construcontrol_project_center/construcontrol_project_center.js",
    "erpnext/construcontrol/page/construcontrol_integrations/construcontrol_integrations.js",
    "erpnext/public/js/construcontrol_mobile.js",
    "erpnext/public/js/construcontrol_finance.js",
    "erpnext/public/js/construcontrol_expenses.js",
    "erpnext/public/js/construcontrol_ux.js",
    "erpnext/public/css/construcontrol.css",
    "erpnext/public/css/construcontrol_finance.css",
    "erpnext/public/css/construcontrol_expenses.css",
    "erpnext/public/css/construcontrol_ux.css",
    "erpnext/public/construcontrol/manifest.webmanifest",
    "erpnext/public/construcontrol/apple-touch-icon-180.png",
    "erpnext/public/construcontrol/icon-192.png",
    "erpnext/public/construcontrol/icon-512.png",
)

REQUIRED_PAGES = (
    "construcontrol-dashboard",
    "construcontrol-profile",
    "construcontrol-project-center",
    "construcontrol-integrations",
    "construcontrol-reporting-center",
    "construcontrol-weekly-closing",
    "construcontrol-migration-console",
)

REQUIRED_TESTS = (
    "test_schema_standalone.py",
    "test_backup_reader_standalone.py",
    "test_normalization_standalone.py",
    "test_catalog_rules_standalone.py",
    "test_runtime_contract_standalone.py",
    "test_migration_safety_standalone.py",
    "test_shell_contract_standalone.py",
    "test_pwa_contract_standalone.py",
    "test_profile_contract_standalone.py",
    "test_finance_contract_standalone.py",
    "test_expense_contract_standalone.py",
    "test_construction_contract_standalone.py",
    "test_integrations_contract_standalone.py",
    "test_executive_contract_standalone.py",
    "test_ux_contract_standalone.py",
)


def text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8", errors="ignore")


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    for relative in REQUIRED_FILES:
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"Falta componente del producto: {relative}")

    tests_dir = ROOT / "erpnext" / "construcontrol" / "tests"
    for filename in REQUIRED_TESTS:
        if not (tests_dir / filename).is_file():
            errors.append(f"Falta prueba obligatoria: {filename}")

    install = text("erpnext/construcontrol/install.py")
    for page in REQUIRED_PAGES:
        if page not in install:
            errors.append(f"La instalación no verifica la página {page}")

    hooks = text("erpnext/hooks.py")
    for asset in (
        "construcontrol_mobile.js",
        "construcontrol_profile_bridge.js",
        "construcontrol_integrations_bridge.js",
        "construcontrol_reports_bridge.js",
        "construcontrol_finance.js",
        "construcontrol_expenses.js",
        "construcontrol_ux.js",
        "construcontrol.css",
        "construcontrol_finance.css",
        "construcontrol_expenses.css",
        "construcontrol_ux.css",
    ):
        if asset not in hooks:
            errors.append(f"El activo no está cargado por hooks.py: {asset}")

    manifest = json.loads(text("erpnext/public/construcontrol/manifest.webmanifest"))
    if manifest.get("display") != "standalone":
        errors.append("La PWA no usa display standalone")
    icon_sizes = {icon.get("sizes") for icon in manifest.get("icons", [])}
    if not {"192x192", "512x512"}.issubset(icon_sizes):
        errors.append("La PWA no declara iconos PNG 192 y 512")

    phase_status = json.loads(text("docs/architecture/phase_status.json"))
    phases = phase_status.get("phases") or []
    if len(phases) != 12:
        errors.append("El seguimiento no contiene exactamente 12 fases")

    migration_files = list((ROOT / "erpnext" / "construcontrol" / "migration").glob("*.py"))
    destructive = re.compile(r"\b(?:DROP\s+TABLE|TRUNCATE\s+TABLE|DELETE\s+FROM)\b", re.IGNORECASE)
    for path in migration_files:
        if destructive.search(path.read_text(encoding="utf-8", errors="ignore")):
            errors.append(f"SQL destructivo detectado en {path.relative_to(ROOT)}")

    user_facing_paths = (
        ROOT / "erpnext" / "public" / "js" / "construcontrol_mobile.js",
        ROOT / "erpnext" / "construcontrol" / "page" / "construcontrol_dashboard" / "construcontrol_dashboard.js",
        ROOT / "erpnext" / "construcontrol" / "page" / "construcontrol_integrations" / "construcontrol_integrations.js",
    )
    for path in user_facing_paths:
        content = path.read_text(encoding="utf-8", errors="ignore")
        if "Integraciones NEXT" in content:
            errors.append(f"Integraciones NEXT volvió a aparecer en {path.relative_to(ROOT)}")

    finance = text("erpnext/construcontrol/finance.py")
    expenses = text("erpnext/construcontrol/expenses.py")
    construction = text("erpnext/construcontrol/construction.py")
    integrations = text("erpnext/construcontrol/integrations.py")
    executive = text("erpnext/construcontrol/executive.py")
    for phrase, content, area in (
        ("net_hnl = net * rate", finance, "tesorería"),
        ("sync_payable_from_expense", expenses, "cuentas por pagar"),
        ("recalculate_project_control", construction, "gestión de obra"),
        ("delete_custom_integration", integrations, "integraciones"),
        ("get_executive_dashboard", executive, "panel ejecutivo"),
    ):
        if phrase not in content:
            errors.append(f"Falta control central de {area}: {phrase}")

    for relative in (
        "erpnext/construcontrol/profile.py",
        "erpnext/construcontrol/finance.py",
        "erpnext/construcontrol/expenses.py",
        "erpnext/construcontrol/construction.py",
        "erpnext/construcontrol/integrations.py",
        "erpnext/construcontrol/executive.py",
    ):
        content = text(relative)
        if re.search(r"\b(?:TODO|FIXME|HACK)\b", content):
            errors.append(f"Marcador de implementación pendiente en {relative}")

    result = {
        "ok": not errors,
        "required_files": len(REQUIRED_FILES),
        "required_pages": len(REQUIRED_PAGES),
        "required_tests": len(REQUIRED_TESTS),
        "warnings": warnings,
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
