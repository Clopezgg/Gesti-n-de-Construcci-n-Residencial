from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAGE = ROOT / "nexora/nexora/page/nexora_finance/nexora_finance.js"
WORKSPACE = ROOT / "nexora/nexora/workspace/nexora/nexora.json"


class TestFinancialUIContract(unittest.TestCase):
	def test_page_calls_real_preview_execute_and_source_services(self) -> None:
		text = PAGE.read_text(encoding="utf-8")
		for method in (
			"nexora.financial.service.preview_central_operation",
			"nexora.financial.service.execute_central_operation",
			"nexora.financial.service.list_central_operations",
			"nexora.financial.service.create_fund_source",
			"nexora.financial.service.list_source_balances",
			"nexora.financial.service.create_commitment",
			"nexora.financial.service.execute_commitment",
			"nexora.financial.service.release_commitment",
		):
			self.assertIn(method, text)
		self.assertNotIn("mock", text.lower())
		self.assertNotIn("simulad", text.lower())

	def test_execute_is_disabled_until_server_preview(self) -> None:
		text = PAGE.read_text(encoding="utf-8")
		self.assertIn('executeButton.prop("disabled", true)', text)
		self.assertIn('executeButton.prop("disabled", false)', text)
		self.assertIn("preview_hash", text)

	def test_operation_type_is_catalog_derived_and_profile_drives_fields(self) -> None:
		text = PAGE.read_text(encoding="utf-8")
		self.assertNotIn('fieldname: "operation_type"', text)
		self.assertIn('fieldname: "kernel_service"', text)
		self.assertIn("read_only: 1", text)
		self.assertIn("serviceForProfile", text)
		self.assertIn("applySelectedProfile", text)
		self.assertIn("applyCategoryVisibility", text)
		self.assertIn("profile.requires_reference", text)
		self.assertIn("profile.requires_due_date", text)
		self.assertIn("profile.requires_beneficiary", text)

	def test_dashboard_launch_context_is_consumed(self) -> None:
		text = PAGE.read_text(encoding="utf-8")
		self.assertIn("frappe.route_options?.nexora_action", text)
		self.assertIn("frappe.route_options?.project", text)
		self.assertIn('launchContext.action === "income"', text)
		self.assertIn('launchContext.action === "expense"', text)
		self.assertIn('operationCode.set_value("CONSTRUCTION_PAYMENT")', text)
		self.assertIn("await project.set_value(launchProject)", text)
		# Si la ruta no trae proyecto, se hereda del contexto activo en lugar de
		# obligar a elegirlo otra vez (salvo que la ruta traiga una acción propia).
		self.assertIn(
			"launchContext.project ||\n"
			"\t\t\t(!launchContext.action ? await window.nexora.context?.activeProject?.() : null) ||\n"
			"\t\t\tnull;",
			text,
		)

	def test_monetary_values_are_formatted_not_raw_interpolated(self) -> None:
		"""Every other NEXORA screen formats HNL amounts through Intl.NumberFormat (or
		the shared window.nexora.ui.formatMoney). A raw `L${value}` interpolation skips
		thousands separators and a fixed decimal count, and interpolates a server value
		straight into HTML instead of through a formatter that only ever returns
		digits, separators and a currency symbol."""
		text = PAGE.read_text(encoding="utf-8")
		self.assertNotRegex(text, r"L\$\{", "found a raw, unformatted HNL interpolation")
		self.assertIn("function money(value)", text)
		self.assertIn("window.nexora.ui?.formatMoney?.(value)", text)

	def test_workspace_links_to_real_page(self) -> None:
		payload = json.loads(WORKSPACE.read_text(encoding="utf-8"))
		shortcut = next(row for row in payload["shortcuts"] if row["label"] == "Núcleo de Fondos")
		self.assertEqual("Page", shortcut["type"])
		self.assertEqual("nexora-finance", shortcut["link_to"])


if __name__ == "__main__":
	unittest.main()
