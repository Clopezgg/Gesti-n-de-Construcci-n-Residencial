#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "erpnext/construcontrol/access.py",
    "erpnext/construcontrol/profile.py",
    "erpnext/construcontrol/users.py",
    "erpnext/construcontrol/business_rules.py",
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
    "erpnext/construcontrol/schema_specialization.py",
    "erpnext/construcontrol/tests/runtime_smoke.py",
    "erpnext/construcontrol/page/construcontrol_dashboard/construcontrol_dashboard.js",
    "erpnext/construcontrol/page/construcontrol_profile/construcontrol_profile.js",
    "erpnext/construcontrol/page/construcontrol_project_center/construcontrol_project_center.js",
    "erpnext/construcontrol/page/construcontrol_integrations/construcontrol_integrations.js",
    "erpnext/construcontrol/page/construcontrol_users/construcontrol_users.js",
    "erpnext/public/js/construcontrol_mobile.js",
    "erpnext/public/js/construcontrol_finance.js",
    "erpnext/public/js/construcontrol_expenses.js",
    "erpnext/public/js/construcontrol_ux.js",
    "erpnext/public/css/construcontrol_canonical.css",
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
    "construcontrol-users",
    "construcontrol-integrations",
    "construcontrol-reporting-center",
    "construcontrol-closing-center",
    "construcontrol-migration-console",
)

REQUIRED_TESTS = (
    "test_access_contract_standalone.py",
    "test_audit_contract_standalone.py",
    "test_backup_reader_standalone.py",
    "test_business_rules_standalone.py",
    "test_catalog_rules_standalone.py",
    "test_completion_markers_standalone.py",
    "test_construction_contract_standalone.py",
    "test_executive_contract_standalone.py",
    "test_expense_contract_standalone.py",
    "test_finance_contract_standalone.py",
    "test_integrations_contract_standalone.py",
    "test_migration_safety_standalone.py",
    "test_normalization_standalone.py",
    "test_profile_contract_standalone.py",
    "test_pwa_contract_standalone.py",
    "test_runtime_contract_standalone.py",
    "test_schema_standalone.py",
    "test_shell_contract_standalone.py",
    "test_users_contract_standalone.py",
    "test_ux_contract_standalone.py",
)


def text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8", errors="ignore")


def function_source(relative: str, function_name: str) -> str:
    source = text(relative)
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return ast.get_source_segment(source, node) or ""
    return ""


def main() -> int:
    errors: list[str] = []

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
        "construcontrol_finance.js",
        "construcontrol_expenses.js",
        "construcontrol_ux.js",
        "construcontrol_canonical.css",
        "construcontrol_finance.css",
        "construcontrol_expenses.css",
        "construcontrol_ux.css",
    ):
        if asset not in hooks:
            errors.append(f"El activo no está cargado por hooks.py: {asset}")
    for obsolete in (
        "erpnext/public/js/construcontrol_profile_bridge.js",
        "erpnext/public/js/construcontrol_integrations_bridge.js",
        "erpnext/public/js/construcontrol_reports_bridge.js",
    ):
        if (ROOT / obsolete).exists() or Path(obsolete).name in hooks:
            errors.append(f"Permanece un bridge de ruta obsoleto: {obsolete}")

    for doctype in (
        "CC Payable Control",
        "CC Construction Phase",
        "CC Procurement Request",
        "CC Progress Update",
        "CC Weekly Closing",
        "CC Project Profile",
        "CC Generated Report",
    ):
        if f'"{doctype}"' not in hooks:
            errors.append(f"Falta autorización de proyecto en escritura: {doctype}")
    if "erpnext.construcontrol.access.validate_document_project_access" not in hooks:
        errors.append("Los documentos operativos no tienen autorización de proyecto en backend")

    reporting_page = text("erpnext/construcontrol/page/construcontrol_reporting_center/construcontrol_reporting_center.js")
    for report_name in (
        "FI03 Cuentas por Pagar",
        "PR02 Presupuesto vs Ejecución",
        "PR03 Fases y Desviaciones",
        "MM03 Inventario Crítico",
        "FI04 Ingresos y Conciliación",
    ):
        if report_name not in reporting_page:
            errors.append(f"El centro de reportes no expone el reporte ejecutivo: {report_name}")

    manifest = json.loads(text("erpnext/public/construcontrol/manifest.webmanifest"))
    if manifest.get("display") != "standalone":
        errors.append("La PWA no usa display standalone")
    if manifest.get("start_url") != "/app/construcontrol-dashboard":
        errors.append("La PWA no inicia en el panel estable de ConstruControl")
    icon_sizes = {icon.get("sizes") for icon in manifest.get("icons", [])}
    if not {"192x192", "512x512"}.issubset(icon_sizes):
        errors.append("La PWA no declara iconos PNG 192 y 512")

    destructive = re.compile(r"\b(?:DROP\s+TABLE|TRUNCATE\s+TABLE|DELETE\s+FROM)\b", re.IGNORECASE)
    for path in (ROOT / "erpnext" / "construcontrol" / "migration").glob("*.py"):
        if destructive.search(path.read_text(encoding="utf-8", errors="ignore")):
            errors.append(f"SQL destructivo detectado en {path.relative_to(ROOT)}")

    dashboard = text("erpnext/construcontrol/page/construcontrol_dashboard/construcontrol_dashboard.js")
    project_page = text("erpnext/construcontrol/page/construcontrol_project_center/construcontrol_project_center.js")
    mobile = text("erpnext/public/js/construcontrol_mobile.js")
    for label, content in (("panel ejecutivo", dashboard), ("centro de proyecto", project_page)):
        if "frappe.dom.freeze" in content or "frappe.dom.unfreeze" in content:
            errors.append(f"{label} todavía contiene bloqueo global")
    if "Módulos ConstruControl" in dashboard or "cc-module-grid" in dashboard:
        errors.append("El panel todavía duplica la navegación")
    compact_mobile = mobile.replace(" ", "")
    if '["List","CCUserAccess"]' in compact_mobile:
        errors.append("Usuarios todavía abre el registro histórico")
    if '"construcontrol-users"' not in mobile:
        errors.append("Usuarios no abre la página canónica")
    if '"construcontrol-integrations"' not in mobile:
        errors.append("Integraciones no abre la página canónica")

    read_service = function_source("erpnext/construcontrol/construction.py", "get_project_center")
    if not read_service:
        errors.append("No existe el servicio de lectura del centro de proyecto")
    elif any(token in read_service for token in (".save(", "db.set_value", "insert(", "delete_doc")):
        errors.append("La consulta del centro de proyecto modifica datos")

    users = text("erpnext/construcontrol/users.py")
    for requirement in (
        '"User"',
        '"Has Role"',
        '"User Permission"',
        "_require_management()",
        "_require_target_management",
        "_set_business_role",
        "_set_project_permission",
    ):
        if requirement not in users:
            errors.append(f"La administración canónica de usuarios no cumple: {requirement}")

    finance = text("erpnext/construcontrol/finance.py")
    expenses = text("erpnext/construcontrol/expenses.py")
    construction = text("erpnext/construcontrol/construction.py")
    integrations = text("erpnext/construcontrol/integrations.py")
    executive = text("erpnext/construcontrol/executive.py")
    importer = text("erpnext/construcontrol/migration/importer.py")
    audit = text("erpnext/construcontrol/audit.py")
    for phrase, content, area in (
        ("net_hnl = net * rate", finance, "tesorería"),
        ("backfill_professional_expenses", expenses, "gastos históricos"),
        ("_require_approver_for_approval_change", expenses, "aprobaciones FI02"),
        ("sync_payable_from_expense", expenses, "cuentas por pagar"),
        ("expense_amounts(", construction, "gestión de obra"),
        ("delete_custom_integration", integrations, "integraciones"),
        ("schedule_status_label", executive, "panel ejecutivo"),
        ("normalize_expense_state", importer, "migración financiera"),
        ("normalize_income_channel", importer, "migración de ingresos"),
        ("credential_secret", audit, "saneamiento de auditoría"),
    ):
        if phrase not in content:
            errors.append(f"Falta control central de {area}: {phrase}")

    for relative in (
        "erpnext/construcontrol/access.py",
        "erpnext/construcontrol/profile.py",
        "erpnext/construcontrol/users.py",
        "erpnext/construcontrol/finance.py",
        "erpnext/construcontrol/expenses.py",
        "erpnext/construcontrol/construction.py",
        "erpnext/construcontrol/integrations.py",
        "erpnext/construcontrol/executive.py",
    ):
        if re.search(r"\b(?:TODO|FIXME|HACK)\b", text(relative)):
            errors.append(f"Marcador pendiente en {relative}")

    result = {
        "ok": not errors,
        "required_files": len(REQUIRED_FILES),
        "required_pages": len(REQUIRED_PAGES),
        "required_tests": len(REQUIRED_TESTS),
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
