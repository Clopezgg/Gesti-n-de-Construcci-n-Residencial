from __future__ import annotations

import json
import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent
PAGE = APP_ROOT / "nexora/page/nexora_operations/nexora_operations.js"
PAGE_JSON = APP_ROOT / "nexora/page/nexora_operations/nexora_operations.json"
UI = APP_ROOT / "public/js/nexora_operational_ui.js"
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

	def test_page_and_assets_are_registered(self) -> None:
		page = json.loads(PAGE_JSON.read_text(encoding="utf-8"))
		self.assertEqual("nexora-operations", page["name"])
		hooks = HOOKS.read_text(encoding="utf-8")
		self.assertIn("nexora_operational.css", hooks)
		self.assertIn("nexora_operational_ui.js", hooks)

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
