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
FINANCE = APP_ROOT / "nexora/page/nexora_finance/nexora_finance.js"
CSS = APP_ROOT / "public/css/nexora_operational.css"
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

	def test_income_entry_points_use_single_101_engine(self) -> None:
		quick = QUICK_FLOWS.read_text(encoding="utf-8")
		page = PAGE.read_text(encoding="utf-8")
		finance = FINANCE.read_text(encoding="utf-8")
		for selector in (
			".nxr-quick-income",
			'[data-action="income"]',
			"[data-launch-income]",
			".nxr-source-create button",
		):
			self.assertIn(selector, quick)
		self.assertIn('movement_code: "101"', quick)
		self.assertIn('frappe.set_route("nexora-operations")', quick)
		self.assertIn("window.nexora.openIncomeDialog = openIncomeFlow", quick)
		self.assertIn("data-nexora-unified-income", quick)
		self.assertIn("Fecha fuera del período activo", quick)
		self.assertIn("nexora_period", quick)
		self.assertNotIn("create_fund_source", quick)
		self.assertIn("nxr-source-create", finance)
		for marker in (
			"preview_operational_movement",
			"execute_operational_movement",
			"preview_hash",
			"idempotency_key",
		):
			self.assertIn(marker, page)

	def test_account_creation_and_selection_are_explicit_and_safe(self) -> None:
		page = PAGE.read_text(encoding="utf-8")
		service = "\n".join(path.read_text(encoding="utf-8") for path in SERVICE_FILES)
		self.assertIn("Usar cuenta existente", page)
		self.assertIn("Crear cuenta nueva", page)
		self.assertIn("Datos manuales, no guardar", page)
		self.assertIn('accountMode === "Existing"', page)
		self.assertIn('accountMode === "New"', page)
		self.assertIn("state.accounts.has", page)
		self.assertIn('options: "Bank"', page)
		self.assertIn("La cuenta frecuente escrita no existe", service)
		self.assertIn('prepared["account_mode"] == "New"', service)

	def test_transaction_layout_has_header_lines_and_detail_panels(self) -> None:
		page = PAGE.read_text(encoding="utf-8")
		css = CSS.read_text(encoding="utf-8")
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
			".nxr-document-tabs",
			".nxr-detail-tabs",
			".nxr-entry-table",
			".nxr-field-invalid",
		):
			self.assertIn(marker, css)

	def test_page_and_assets_are_registered(self) -> None:
		page = json.loads(PAGE_JSON.read_text(encoding="utf-8"))
		self.assertEqual("nexora-operations", page["name"])
		hooks = HOOKS.read_text(encoding="utf-8")
		self.assertIn("nexora_operational.css", hooks)
		self.assertIn("nexora_operational_ui.js", hooks)
		self.assertIn("nexora_quick_flows.js", hooks)

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
