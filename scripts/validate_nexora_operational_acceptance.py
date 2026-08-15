#!/usr/bin/env python3
"""Validate current NEXORA operational and pre-deploy repository contracts.

The gate follows the canonical guided operation engine, permission-aware services,
responsive/PWA assets and final delivery tooling. It does not validate retired
quick dialogs or implementation details that were intentionally replaced.
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


EXTERNAL_ACTIVATION_STATUS = "IMPLEMENTADO — ACTIVACIÓN EXTERNA PENDIENTE"


def validate_requirement_matrix() -> None:
	path = require_file("docs/nexora/MATRIZ_REQUISITOS.md")
	if not path.is_file():
		return
	text = path.read_text(encoding="utf-8")
	accepted = (
		"IMPLEMENTADO Y VALIDADO",
		"OBSOLETO JUSTIFICADO",
		"NO APLICA JUSTIFICADO",
		EXTERNAL_ACTIVATION_STATUS,
	)
	identifiers: set[str] = set()
	for line in text.splitlines():
		if not line.startswith("| `NXR-"):
			continue
		# Columnas reales de la fila (ID, Título, Estado, ...), no una búsqueda de
		# subcadena sobre la línea completa: el texto libre de "Aceptación verificable"
		# puede mencionar el nombre de un estado terminal (p. ej. al documentar una
		# corrección de clasificación) sin que la fila esté realmente en ese estado.
		cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
		identifier_match = re.search(r"NXR-[A-Z]+-\d+", cells[0]) if cells else None
		if not identifier_match:
			continue
		identifier = identifier_match.group(0)
		identifiers.add(identifier)
		estado = cells[2].strip() if len(cells) > 2 else ""
		if estado not in accepted:
			ERRORS.append(f"Requirement without terminal justified status: {identifier}")
		elif estado == EXTERNAL_ACTIVATION_STATUS:
			# Este estado existe solo para software real y probado que depende de
			# una activación externa que únicamente el propietario puede completar
			# (credenciales/token/verificación reales de un tercero) — nunca para
			# disfrazar una brecha de construcción real como "pendiente externo".
			# Se exige en el texto libre de evidencia (última columna), no en el
			# nombre del propio estado: "ACTIVACIÓN EXTERNA" ya aparece ahí por
			# definición, así que comprobarlo contra la fila completa nunca
			# fallaría — la fila debe declarar ambas cosas de verdad, en prosa.
			evidence = cells[-1] if cells else ""
			if "CONSTRUCCIÓN: 100%" not in evidence:
				ERRORS.append(
					f"{identifier}: usa {EXTERNAL_ACTIVATION_STATUS!r} sin declarar "
					f"'CONSTRUCCIÓN: 100%' explícito en su evidencia."
				)
			if "ACTIVACIÓN EXTERNA" not in evidence:
				ERRORS.append(
					f"{identifier}: usa {EXTERNAL_ACTIVATION_STATUS!r} sin nombrar la "
					f"dependencia externa real ('ACTIVACIÓN EXTERNA') que falta."
				)
	if len(identifiers) != 187:
		ERRORS.append(f"Requirement matrix coverage is incomplete: {len(identifiers)} requirements found")


def validate_financial_engine() -> None:
	require_markers(
		"nexora_app/nexora/financial/service.py",
		(
			"create_fund_source",
			"preview_central_operation",
			"execute_central_operation",
			"create_commitment",
			"execute_commitment",
			"release_commitment",
			"preview_operational_movement",
			"execute_operational_movement",
			"list_financial_accounts",
			"get_financial_account",
		),
	)
	require_markers(
		"nexora_app/nexora/financial/operational_commands.py",
		(
			"def preview_operational_movement",
			"def execute_operational_movement",
			"require_project_access",
			"preview_hash",
			"idempotency_key",
			"_resolve_expense_account",
			"rollback(point)",
		),
	)
	require_markers(
		"nexora_app/nexora/financial/operational_income.py",
		(
			"def income_preview",
			"def execute_income",
			"require_project_access",
			"preview_hash",
			"idempotency_key",
			"rollback(point)",
		),
	)
	require_markers(
		"nexora_app/nexora/financial/operational_accounts.py",
		(
			"def list_financial_accounts",
			"def get_financial_account",
			"frappe.get_list",
			"frappe.has_permission",
			"require_project_access",
			"requested_currency",
			"requested_channel",
			"requested_counterparty",
			"_masked_account",
		),
	)


def validate_guided_operations() -> None:
	require_markers(
		"nexora_app/nexora/public/js/nexora_quick_flows.js",
		(
			'openOperationalFlow("101")',
			'openOperationalFlow("102")',
			'frappe.set_route("nexora-operations")',
			"executionInFlight",
			"idempotency_key",
		),
	)
	require_markers(
		"nexora_app/nexora/public/js/nexora_guided_model.js",
		(
			"accountCompatible",
			"canonicalAccountSelection",
			"movementDirection",
			"conditionalVisibility",
			"fieldStage",
		),
	)
	require_markers(
		"nexora_app/nexora/public/js/nexora_guided_operations.js",
		(
			"Cuenta para esta operación",
			"Seleccionar una cuenta guardada",
			"Usar otros datos bancarios",
			"Sí, guardar para el futuro",
			"No, usar solo esta vez",
			'data-guided-stage="1"',
			'data-guided-stage="2"',
			'data-guided-stage="3"',
			'data-guided-stage="4"',
			"Opciones avanzadas",
			".nxr-preview-movement",
			".nxr-execute-movement",
			"revealFirstError",
			"nexora.financial.service.list_financial_accounts",
			"nexora.financial.service.get_financial_account",
		),
	)
	require_markers(
		"nexora_app/nexora/nexora/page/nexora_operations/nexora_operations.js",
		(
			"preview_operational_movement",
			"execute_operational_movement",
			"preview_hash",
			"idempotency_key",
			"allocations()",
		),
	)
	require_markers(
		"nexora_app/nexora/public/css/nexora_guided_operations.css",
		(
			"@media (max-width: 760px)",
			"env(safe-area-inset-bottom",
			"min-height: 44px",
			"touch-action: manipulation",
			"prefers-reduced-motion",
		),
	)


def validate_business_surfaces() -> None:
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
		"nexora_app/nexora/nexora/page/nexora_reports/nexora_reports.js",
	)
	for relative in pages:
		require_markers(relative, ("frappe.pages", "frappe.call"))


def validate_dashboard_and_search() -> None:
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
		"nexora_app/nexora/nexora/page/nexora_dashboard/nexora_dashboard.js",
		(
			"finance.total_available_hnl",
			"executive.spent_hnl",
			"budgets.total_available_hnl",
			"pending_accounts",
			"progress.physical_percent",
			"nxr-evidence-gallery",
			"nxr-alert-rows",
			"nxr-contract-rows",
			'data-action="income"',
			'data-action="expense"',
		),
	)
	require_markers(
		"nexora_app/nexora/permissions.py",
		(
			"def secure_universal_search",
			"def secure_universal_search_consolidated",
			"frappe.has_permission",
			"require_project_access",
			"_masked_account",
		),
	)


def validate_pwa_and_browser() -> None:
	require_file("nexora_app/nexora/public/manifest.json")
	require_file("nexora_app/nexora/www/nexora-service-worker.js")
	require_markers(
		"scripts/nexora_browser_smoke.mjs",
		(
			"chromium",
			"webkit",
			"validatePwa",
			"validateIncomeGuided",
			"validateExpenseGuided",
			"nexora-dashboard",
			"/^\\d{12}$/",
		),
	)
	require_markers(
		".github/workflows/nexora-app.yml",
		("Frappe real · escritorio · tableta · iPhone · PWA", "nexora_browser_smoke.mjs", "playwright"),
	)
	for relative in (
		"nexora_app/nexora/public/manifest.json",
		"nexora_app/nexora/nexora/workspace/nexora/nexora.json",
	):
		path = require_file(relative)
		if path.is_file():
			try:
				json.loads(path.read_text(encoding="utf-8"))
			except Exception as exc:
				ERRORS.append(f"Invalid JSON {relative}: {exc}")


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


def main() -> int:
	validate_requirement_matrix()
	validate_financial_engine()
	validate_guided_operations()
	validate_business_surfaces()
	validate_dashboard_and_search()
	validate_pwa_and_browser()
	validate_delivery_contract()

	print(f"NEXORA operational acceptance: {len(ERRORS)} error(s)")
	for error in ERRORS:
		print(f"- {error}")
	return 1 if ERRORS else 0


if __name__ == "__main__":
	sys.exit(main())
