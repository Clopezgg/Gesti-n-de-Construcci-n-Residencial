from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.close.service import correct_weekly_close, save_weekly_close
from nexora.financial.sources import create_fund_source
from nexora.permissions import require_project_access
from nexora.reports.service import export_report, reconcile_fund_source, save_report_definition


def _key(prefix: str) -> str:
	return f"{prefix}-{uuid.uuid4().hex}"


def _ensure_user(email: str, role: str) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@", 1)[0],
				"enabled": 1,
				"send_welcome_email": 0,
				"roles": [{"role": role}],
			}
		).insert(ignore_permissions=True)
	return email


class TestExecutiveReportingMariaDB(FrappeTestCase):
	def setUp(self) -> None:
		super().setUp()
		frappe.set_user("Administrator")
		marker = uuid.uuid4().hex[:10]
		self.project = str(
			frappe.get_doc(
				{
					"doctype": "Project",
					"project_name": f"_Test NEXORA Executive {marker}",
					"status": "Open",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		self.operator = _ensure_user(
			f"nxr-executive-operator-{marker}@example.test",
			"NEXORA Finance Operator",
		)
		self.manager = _ensure_user(
			f"nxr-executive-manager-{marker}@example.test",
			"NEXORA Finance Manager",
		)
		self.viewer = _ensure_user(
			f"nxr-executive-viewer-{marker}@example.test",
			"NEXORA Project Viewer",
		)

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def test_project_viewer_requires_explicit_project_scope(self) -> None:
		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			require_project_access(None, action="view_reports")
		with self.assertRaises(frappe.PermissionError):
			require_project_access(self.project, action="view_reports")

		frappe.set_user("Administrator")
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": self.viewer,
				"allow": "Project",
				"for_value": self.project,
			}
		).insert(ignore_permissions=True)
		frappe.set_user(self.viewer)
		require_project_access(self.project, action="view_reports")

	def test_finance_manager_can_read_any_existing_project(self) -> None:
		frappe.set_user(self.manager)
		require_project_access(self.project, action="view_reports")
		require_project_access(None, action="view_reports")

	def test_reconciliation_is_explicit_audited_and_validated(self) -> None:
		frappe.set_user(self.operator)
		source = str(
			create_fund_source(
				{
					"idempotency_key": _key("reconciliation-source"),
					"source_name": "Remesa por conciliar",
					"channel": "Remittance",
					"project": self.project,
					"currency": "HNL",
					"original_amount": 250,
					"exchange_rate": 1,
					"origin_or_sender": "Prueba conciliación",
					"custodian": self.operator,
				}
			)["fund_source"]
		)
		frappe.set_user(self.manager)
		with self.assertRaises(frappe.ValidationError):
			reconcile_fund_source(
				{
					"source": source,
					"status": "Disputed",
					"method": "Bank Statement",
					"difference_hnl": 10,
					"note": "Diferencia detectada",
					"idempotency_key": _key("reconciliation-invalid"),
				}
			)

		result = reconcile_fund_source(
			{
				"source": source,
				"status": "Reconciled",
				"method": "Remittance Statement",
				"difference_hnl": 0,
				"idempotency_key": _key("reconciliation-valid"),
			}
		)
		self.assertEqual("Reconciled", result["reconciliation_status"])
		self.assertEqual(self.manager, result["reconciled_by"])
		self.assertTrue(frappe.db.exists("NXR Audit Event", {"event_type": "fund_source_reconciled"}))

	def test_weekly_close_is_idempotent_immutable_and_correctable(self) -> None:
		frappe.set_user(self.manager)
		week_end = frappe.utils.today()
		week_start = frappe.utils.add_days(week_end, -6)
		key = _key("weekly-close")
		payload = {
			"project": self.project,
			"week_start": week_start,
			"week_end": week_end,
			"comments": "Cierre de aceptación",
			"idempotency_key": key,
		}
		first = save_weekly_close(payload)
		second = save_weekly_close(payload)
		self.assertEqual(first, second)
		self.assertEqual(12, len(first["document_number"]))
		self.assertTrue(first["document_number"].isdigit())

		with self.assertRaises(frappe.ValidationError):
			save_weekly_close({**payload, "idempotency_key": _key("duplicate-period")})

		correction = correct_weekly_close(
			{
				**payload,
				"weekly_close": first["weekly_close"],
				"correction_reason": "Corrección por conciliación posterior",
				"idempotency_key": _key("weekly-correction"),
			}
		)
		self.assertEqual("Correction", correction["status"])
		self.assertNotEqual(first["weekly_close"], correction["weekly_close"])

		doc = frappe.get_doc("NXR Weekly Close", first["weekly_close"])
		doc.comments = "Edición prohibida"
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)

	def test_saved_report_and_excel_export_are_server_side(self) -> None:
		frappe.set_user(self.manager)
		definition = save_report_definition(
			{
				"title": "BI01 aceptación",
				"report_code": "BI01",
				"project": self.project,
				"filters": {"project": self.project},
				"idempotency_key": _key("saved-report"),
			}
		)
		self.assertEqual(12, len(definition["document_number"]))
		self.assertTrue(definition["document_number"].isdigit())

		export_report(
			{
				"report_code": "BI01",
				"format": "xlsx",
				"project": self.project,
			}
		)
		self.assertTrue(frappe.local.response.filename.endswith(".xlsx"))
		self.assertTrue(frappe.local.response.filecontent)
		self.assertEqual("download", frappe.local.response.type)

		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			export_report(
				{
					"report_code": "BI01",
					"format": "xlsx",
					"project": self.project,
				}
			)
