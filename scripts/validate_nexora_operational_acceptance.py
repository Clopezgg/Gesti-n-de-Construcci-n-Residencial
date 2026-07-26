#!/usr/bin/env python3
"""NEXORA operational acceptance gate.

This gate verifies that the integrated product exposes the daily workflows,
server-side services, canonical navigation, mobile/PWA assets, final evidence
and delivery tooling required for Phases 2 and 3. It intentionally validates
real repository contracts instead of trusting status labels alone.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []


def require_file(relative: str) -> Path:
    path = ROOT / relative
    if not path.is_file():
        ERRORS.append(f"Missing required file: {relative}")
    return path


def require_markers(relative: str, markers: tuple[str, ...]) -> None:
    path = require_file(relative)
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    for marker in markers:
        if marker not in text:
            ERRORS.append(f"{relative} is missing required marker: {marker}")


def validate_requirement_matrix() -> None:
    path = require_file("docs/nexora/MATRIZ_REQUISITOS.md")
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    rows = re.findall(r"\|\s*(NXR-[A-Z]+-\d+)\s*\|([^\n]+)", text)
    identifiers = {identifier for identifier, _ in rows}
    if len(identifiers) < 160:
        ERRORS.append(f"Requirement matrix coverage is incomplete: {len(identifiers)} requirements found")
    accepted = ("IMPLEMENTADO Y VALIDADO", "OBSOLETO JUSTIFICADO", "NO APLICA JUSTIFICADO")
    for line in text.splitlines():
        match = re.search(r"\|\s*(NXR-[A-Z]+-\d+)\s*\|", line)
        if match and not any(status in line for status in accepted):
            ERRORS.append(f"Requirement without terminal justified status: {match.group(1)}")


def validate_phase_two_workflows() -> None:
    require_markers(
        "nexora_app/nexora/financial/service.py",
        (
            "def create_fund_source",
            "def preview_central_operation",
            "def execute_central_operation",
            "def create_commitment",
            "def execute_commitment",
            "def release_commitment",
            "require_action",
            "idempotency",
        ),
    )
    require_markers(
        "nexora_app/nexora/nexora/page/nexora_finance/nexora_finance.js",
        (
            'title: __("Fondos y operaciones")',
            'launchContext.action === "income"',
            'launchContext.action === "expense"',
            "create_fund_source",
            "preview_central_operation",
            "execute_central_operation",
            "idempotency_key",
            "evidence",
        ),
    )
    require_markers(
        "nexora_app/nexora/public/js/nexora.js",
        (
            'title: __("Registrar ingreso")',
            'label: __("Monto recibido")',
            'label: __("Cómo se recibió")',
            'label: __("Remitente u origen")',
            'title: __("Registrar gasto")',
            'label: __("Monto pagado")',
            'label: __("Fondo que pagará")',
            'label: __("Categoría del gasto")',
            'label: __("Comprobante")',
            'operation_code: "CONSTRUCTION_PAYMENT"',
            "nexora.financial.service.create_fund_source",
            "nexora.financial.service.preview_central_operation",
            "nexora.financial.service.execute_central_operation",
            "idempotency_key: uuid()",
            "preview_hash: preview.message.preview_hash",
        ),
    )

    surfaces = {
        "nexora_app/nexora/contracts/service.py": ("require_action", "frappe.whitelist"),
        "nexora_app/nexora/purchases/service.py": ("require_action", "frappe.whitelist"),
        "nexora_app/nexora/inventory/service.py": ("require_action", "frappe.whitelist"),
        "nexora_app/nexora/budget/service.py": ("require_action", "frappe.whitelist"),
        "nexora_app/nexora/progress/service.py": ("require_action", "frappe.whitelist"),
        "nexora_app/nexora/reports/service.py": ("require_action", "frappe.whitelist"),
    }
    for relative, markers in surfaces.items():
        require_markers(relative, markers)

    pages = (
        "nexora_app/nexora/nexora/page/nexora_contracts/nexora_contracts.js",
        "nexora_app/nexora/nexora/page/nexora_suppliers/nexora_suppliers.js",
        "nexora_app/nexora/nexora/page/nexora_purchase_requests/nexora_purchase_requests.js",
        "nexora_app/nexora/nexora/page/nexora_evidence/nexora_evidence.js",
        "nexora_app/nexora/nexora/page/nexora-reports/nexora-reports.js",
    )
    for relative in pages:
        require_markers(relative, ("frappe.pages", "frappe.call"))


def validate_phase_three_product() -> None:
    require_markers(
        "nexora_app/nexora/dashboard/service.py",
        (
            "def get_dashboard_summary",
            "source_states",
            '"NXR Operation Effect"',
            '"NXR Contract Estimate"',
            '"NXR Progress Record"',
            '"NXR Evidence"',
        ),
    )
    require_markers(
        "nexora_app/nexora/nexora/page/nexora-dashboard/nexora-dashboard.js",
        (
            "finance.total_available_hnl",
            "budgets.total_executed_hnl",
            "pending_accounts",
            "progress.physical_percent",
            "nxr-evidence-gallery",
            "nxr-alert-rows",
            "nxr-contract-rows",
        ),
    )
    require_markers(
        "nexora_app/nexora/public/js/nexora.js",
        (
            "/app/nexora-dashboard",
            "/app/nexora-finance",
            "/app/nexora-contracts",
            "/app/nexora-suppliers",
            "/app/nexora-evidence",
            "/app/nexora-reports",
            "window.nexora.openIncomeDialog",
            "window.nexora.openExpenseDialog",
        ),
    )
    require_markers(
        "nexora_app/nexora/install.py",
        ("NEXORA_HOME_PAGE", 'frappe.db.set_default("desktop:home_page"'),
    )
    require_file("nexora_app/nexora/public/css/nexora.css")
    require_file("nexora_app/nexora/www/manifest.json")
    require_file("nexora_app/nexora/www/nexora-service-worker.js")
    require_markers(
        "scripts/nexora_browser_smoke.mjs",
        ("chromium", "webkit", "serviceWorker", "nexora-dashboard"),
    )
    require_markers(
        ".github/workflows/nexora-app.yml",
        ("Frappe real · escritorio · iPhone · PWA", "nexora_browser_smoke.mjs", "playwright"),
    )


def validate_delivery_contract() -> None:
    for relative in (
        "docs/final/NEXORA_ENTREGA_FINAL.md",
        "docs/final/NEXORA_MANUAL_USUARIO.md",
        "docs/final/NEXORA_MANUAL_ADMINISTRADOR.md",
        "docs/final/NEXORA_OPERACION_Y_RESPALDO.md",
        "docs/final/NEXORA_MATRIZ_FINAL_CUMPLIMIENTO.md",
        "scripts/build_nexora_release.py",
        "scripts/verify_nexora_deployment.py",
        "nexora_app/nexora/build_info.py",
        "nexora_app/nexora/tests/test_build_info_contract.py",
        ".github/workflows/nexora-final-delivery.yml",
        ".github/workflows/nexora-deployment-verification.yml",
    ):
        require_file(relative)
    require_markers(
        "nexora_app/nexora/build_info.py",
        ("get_build_info", "NEXORA_BUILD_SHA", "NEXORA_ENVIRONMENT", '"product": "NEXORA"'),
    )
    require_markers(
        "scripts/verify_nexora_deployment.py",
        ("api/method/ping", "nexora.build_info.get_build_info", "app/nexora-dashboard", "expected-sha"),
    )


def validate_json_assets() -> None:
    for relative in (
        "nexora_app/nexora/www/manifest.json",
        "nexora_app/nexora/nexora/workspace/nexora/nexora.json",
    ):
        path = require_file(relative)
        if path.is_file():
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                ERRORS.append(f"Invalid JSON {relative}: {exc}")


def main() -> int:
    validate_requirement_matrix()
    validate_phase_two_workflows()
    validate_phase_three_product()
    validate_delivery_contract()
    validate_json_assets()

    print(f"NEXORA operational acceptance: {len(ERRORS)} error(s)")
    for error in ERRORS:
        print(f"- {error}")
    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
