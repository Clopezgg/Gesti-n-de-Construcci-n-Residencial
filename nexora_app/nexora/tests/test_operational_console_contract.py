from __future__ import annotations

import json
import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent
PAGE = APP_ROOT / "nexora/page/nexora_operations/nexora_operations.js"
PAGE_JSON = APP_ROOT / "nexora/page/nexora_operations/nexora_operations.json"
UI = APP_ROOT / "public/js/nexora_operational_ui.js"
QUICK_FLOWS = APP_ROOT / "public/js/nexora_quick_flows.js"
GUIDED = APP_ROOT / "public/js/nexora_guided_operations.js"
FINANCE = APP_ROOT / "nexora/page/nexora_finance/nexora_finance.js"
CSS = APP_ROOT / "public/css/nexora_operational.css"
GUIDED_CSS = APP_ROOT / "public/css/nexora_guided_operations.css"
SERVICE_FILES = [
	APP_ROOT / "financial/operational.py",
	APP_ROOT / "financial/operational_accounts.py",
	APP_ROOT / "financial/operational_commands.py",
	APP_ROOT / "financial/operational_common.py",
	APP_ROOT / "financial/operational_ledger.py",
	APP_ROOT / "financial/operational_income.py",
	APP_ROOT / "financial/operational_metadata.py",
]
HOOKS = APP_ROOT / "hooks.py"
ACCOUNT = APP_ROOT / "nexora/doctype/nxr_financial_account/nxr_financial_account.json"
METADATA = APP_ROOT / "nexora/doctype/nxr_operation_metadata/nxr_operation_metadata.json"
SOURCES = APP_ROOT / "financial/sources.py"


class TestOperationalConsoleContract(unittest.TestCase):
	def test_numeric_movement_console_is_real_and_server_backed(self) -> None:
		text = PAGE.read_text(encoding="utf-8")
		for code in ("101", "102", "303", "304", "501"):
			self.assertIn(code, text)
		for field in (
			"movement_code",
			"document_date",
			"account_mode",
			"financial_account",
			"origin_or_sender",
			"institution",
			"account_reference",
			"reference_name",
		):
			self.assertIn(field, text)
		for method in (
			"preview_operational_movement",
			"execute_operational_movement",
			"list_financial_accounts",
			"list_operational_ledger",
		):
			self.assertIn(method, text)
		self.assertIn("preview_hash", text)
		self.assertIn('prop("disabled", true)', text)
		self.assertNotIn("mock", text.lower())
		self.assertNotIn("simulad", text.lower())

	def test_income_and_expense_entry_points_use_single_operational_engine(self) -> None:
		quick = QUICK_FLOWS.read_text(encoding="utf-8")
		page = PAGE.read_text(encoding="utf-8")
		finance = FINANCE.read_text(encoding="utf-8")
		for selector in (
			".nxr-quick-income",
			'[data-action="income"]',
			"[data-launch-income]",
			".nxr-source-create button",
			".nxr-quick-expense",
			'[data-action="expense"]',
		):
			self.assertIn(selector, quick)
		for marker in (
			'openOperationalFlow("101")',
			'openOperationalFlow("102")',
			"movement_code: movementCode",
			'frappe.set_route("nexora-operations")',
			"window.nexora.openIncomeFlow",
			"window.nexora.openExpenseFlow",
			"data-nexora-unified-income",
			"Fecha fuera del período activo",
			"nexora_period",
		):
			self.assertIn(marker, quick)
		self.assertNotIn("create_fund_source", quick)
		self.assertIn("nxr-source-create", finance)
		for marker in (
			"preview_operational_movement",
			"execute_operational_movement",
			"preview_hash",
			"idempotency_key",
		):
			self.assertIn(marker, page)

	def test_account_selection_is_human_visible_and_server_safe(self) -> None:
		page = PAGE.read_text(encoding="utf-8")
		guided = GUIDED.read_text(encoding="utf-8")
		accounts = (APP_ROOT / "financial/operational_accounts.py").read_text(encoding="utf-8")
		commands = (APP_ROOT / "financial/operational_commands.py").read_text(encoding="utf-8")
		for label in (
			"Cuenta para esta operación",
			"Seleccionar una cuenta guardada",
			"Usar otros datos bancarios",
			"Sí, guardar para el futuro",
			"No, usar solo esta vez",
		):
			self.assertIn(label, guided)
		for technical_label in (
			"Usar cuenta existente",
			"Crear cuenta nueva",
			"Datos manuales, no guardar",
		):
			self.assertNotIn(technical_label, guided)
		self.assertIn('accountMode === "Existing"', page)
		self.assertIn('accountMode === "New"', page)
		self.assertIn("technicalMode.hidden = true", guided)
		self.assertIn("savedControl.hidden = true", guided)
		for marker in (
			"frappe.has_permission",
			"require_project_access",
			"requested_currency",
			"requested_channel",
			"requested_counterparty",
			"La cuenta guardada no pertenece al proyecto seleccionado",
			"La cuenta seleccionada no es compatible con la moneda",
			"_masked_account",
		):
			self.assertIn(marker, accounts)
		self.assertIn("_resolve_expense_account", commands)
		self.assertIn('prepared.get("account_mode") == "New"', commands)

	def test_progressive_layout_hides_internal_tabs_but_preserves_canonical_model(self) -> None:
		page = PAGE.read_text(encoding="utf-8")
		guided = GUIDED.read_text(encoding="utf-8")
		css = GUIDED_CSS.read_text(encoding="utf-8")
		for marker in (
			'data-document-tab="general"',
			'data-document-tab="evidence"',
			'data-detail-tab="account"',
			'data-detail-tab="amount"',
			'data-detail-tab="classification"',
			'data-detail-tab="funds"',
			"nxr-entry-table",
			"nxr-validation-summary",
		):
			self.assertIn(marker, page)
		for marker in (
			'data-guided-stage="1"',
			'data-guided-stage="2"',
			'data-guided-stage="3"',
			'data-guided-stage="4"',
			"Opciones avanzadas",
			"nxr-guided-legacy-hidden",
			"revealFirstError",
		):
			self.assertIn(marker, guided + css)

	def test_page_and_assets_are_registered(self) -> None:
		page = json.loads(PAGE_JSON.read_text(encoding="utf-8"))
		self.assertEqual("nexora-operations", page["name"])
		hooks = HOOKS.read_text(encoding="utf-8")
		for asset in (
			"nexora_operational.css",
			"nexora_guided_operations.css",
			"nexora_operational_ui.js",
			"nexora_quick_flows.js",
			"nexora_guided_model.js",
			"nexora_guided_operations.js",
		):
			self.assertIn(asset, hooks)

	def test_dashboard_routes_daily_actions_and_compacts_cards(self) -> None:
		ui = UI.read_text(encoding="utf-8")
		css = CSS.read_text(encoding="utf-8")
		self.assertIn('frappe.set_route("nexora-operations")', ui)
		self.assertIn('data-action="income"', ui)
		self.assertIn('data-action="expense"', ui)
		self.assertIn("rows.slice(0, 3)", ui)
		self.assertIn("Ver más actividad", ui)
		for heading in (
			"Día",
			"Fecha documento",
			"Mov.",
			"Remitente / beneficiario",
			"Institución",
			"Cuenta",
			"Moneda",
		):
			self.assertIn(heading, ui)
		self.assertIn("grid-auto-rows: minmax(0, 1fr)", css)
		self.assertIn("height: 100%", css)

	def test_accounts_and_operation_codes_are_canonical_service_records(self) -> None:
		account = json.loads(ACCOUNT.read_text(encoding="utf-8"))
		metadata = json.loads(METADATA.read_text(encoding="utf-8"))
		self.assertTrue(
			next(row for row in account["fields"] if row["fieldname"] == "account_fingerprint")["unique"]
		)
		self.assertTrue(next(row for row in metadata["fields"] if row["fieldname"] == "operation")["unique"])
		self.assertIn(
			"101\n102\n303\n304\n501",
			next(row for row in metadata["fields"] if row["fieldname"] == "movement_code")["options"],
		)
		self.assertTrue(all(not row.get("create") and not row.get("write") for row in account["permissions"]))
		read_roles = {row["role"] for row in account["permissions"] if row.get("read")}
		self.assertEqual(
			{"NEXORA Administrator", "NEXORA Finance Manager", "NEXORA Finance Operator"},
			read_roles,
		)
		self.assertTrue(
			all(not row.get("create") and not row.get("write") for row in metadata["permissions"])
		)

	def test_server_preserves_audit_and_never_physically_deletes_posted_operations(self) -> None:
		service = "\n".join(path.read_text(encoding="utf-8") for path in SERVICE_FILES)
		sources = SOURCES.read_text(encoding="utf-8")
		self.assertIn("NXR Operation Metadata", service)
		self.assertIn("NXR Monthly Close", service)
		self.assertIn("registered_at", service)
		self.assertIn("operation_date: str | None = None", sources)
		for forbidden in ("delete_doc(", "db.delete(", "frappe.delete_doc("):
			self.assertNotIn(forbidden, service)


if __name__ == "__main__":
	unittest.main()
