from __future__ import annotations

import uuid
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.close.service import correct_weekly_close, save_weekly_close
from nexora.dashboard.executive import get_executive_snapshot, get_source_statement_page
from nexora.dashboard.expense_query import get_expense_page
from nexora.financial.operations import execute_financial_operation
from nexora.financial.sources import cancel_fund_source, create_fund_source
from nexora.permissions import require_project_access
from nexora.reports.actions import archive_saved_report
from nexora.reports.safe_export import (
	PAGINATED_REPORT_LOADERS,
	_assert_export_size,
	export_report,
)
from nexora.reports.service import (
	list_saved_reports,
	reconcile_fund_source,
	save_report_definition,
)


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

	def _source(self, *, source_date: str | None = None, amount: int = 250) -> str:
		frappe.set_user(self.operator)
		return str(
			create_fund_source(
				{
					"idempotency_key": _key("executive-source"),
					"source_name": f"Fuente ejecutiva {uuid.uuid4().hex[:8]}",
					"channel": "Remittance",
					"project": self.project,
					"source_date": source_date or frappe.utils.today(),
					"currency": "HNL",
					"original_amount": amount,
					"exchange_rate": 1,
					"origin_or_sender": "Prueba ejecutiva",
					"custodian": self.operator,
				}
			)["fund_source"]
		)

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
		source = self._source()
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

	def test_historical_statement_excludes_future_sources_and_separates_reversal(self) -> None:
		future_date = frappe.utils.add_days(frappe.utils.today(), 7)
		future_source = self._source(source_date=future_date, amount=900)
		future_operation = frappe.db.get_value(
			"NXR Operation Effect", {"fund_source": future_source, "effect_type": "Received"}, "operation"
		)
		self.assertEqual(
			frappe.utils.getdate(future_date),
			frappe.utils.getdate(frappe.db.get_value("NXR Operation", future_operation, "operation_date")),
		)
		cancelled_source = self._source(amount=400)
		frappe.set_user(self.manager)
		cancel_fund_source(
			cancelled_source,
			"Ingreso duplicado detectado durante la validación",
			_key("cancel-source"),
		)
		period = {
			"project": self.project,
			"from_date": frappe.utils.add_days(frappe.utils.today(), -1),
			"to_date": frappe.utils.today(),
			"page": 1,
			"page_size": 100,
		}
		statement = get_source_statement_page(period)
		names = {row["name"] for row in statement["rows"]}
		self.assertNotIn(future_source, names)
		row = next(row for row in statement["rows"] if row["name"] == cancelled_source)
		self.assertEqual(400, row["received_hnl"])
		self.assertEqual(400, row["reversed_hnl"])
		self.assertEqual(0, row["spent_hnl"])
		self.assertEqual(0, row["closing_funds_hnl"])
		self.assertEqual("Cancelled", row["status"])

		snapshot = get_executive_snapshot(period)
		self.assertEqual(0, snapshot["executive"]["cash_available_hnl"])
		self.assertEqual(
			snapshot["executive"]["cash_available_hnl"],
			snapshot["executive"]["projected_available_hnl"],
		)
		self.assertIn("pending_obligations_hnl", snapshot["executive"])

	def test_fi02_source_filter_sums_only_the_selected_allocation(self) -> None:
		first = self._source(amount=600)
		second = self._source(amount=400)
		frappe.set_user(self.operator)
		execute_financial_operation(
			{
				"idempotency_key": _key("fi02-multisource"),
				"operation_type": "Outflow",
				"project": self.project,
				"operation_date": frappe.utils.today(),
				"amount_hnl": 100,
				"allocations": [
					{"source": first, "amount_hnl": 60},
					{"source": second, "amount_hnl": 40},
				],
				"requester": self.operator,
				"approved_by": self.manager,
			}
		)
		base = {
			"project": self.project,
			"from_date": frappe.utils.today(),
			"to_date": frappe.utils.today(),
			"page": 1,
			"page_size": 100,
		}
		all_rows = get_expense_page(base)
		self.assertEqual(100, all_rows["summary"]["amount_hnl"])
		first_rows = get_expense_page({**base, "source": first})
		self.assertEqual(60, first_rows["summary"]["amount_hnl"])
		self.assertEqual(first, first_rows["rows"][0]["sources"])
		second_rows = get_expense_page({**base, "source": second})
		self.assertEqual(40, second_rows["summary"]["amount_hnl"])
		self.assertEqual(second, second_rows["rows"][0]["sources"])

		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			get_expense_page({**base, "source": first})

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
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("NXR Weekly Close", first["weekly_close"], ignore_permissions=True)

	def test_saved_report_can_be_archived_but_not_deleted(self) -> None:
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
		archive_payload = {
			"saved_report": definition["saved_report"],
			"idempotency_key": _key("archive-report"),
		}
		first = archive_saved_report(archive_payload)
		self.assertEqual(first, archive_saved_report(archive_payload))
		self.assertEqual("Archived", first["status"])
		self.assertFalse(
			any(row["name"] == definition["saved_report"] for row in list_saved_reports({"project": self.project}))
		)
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("NXR Saved Report", definition["saved_report"], ignore_permissions=True)

		second = save_report_definition(
			{
				"title": "FI01 privado",
				"report_code": "FI01",
				"project": self.project,
				"filters": {"project": self.project},
				"idempotency_key": _key("saved-report-private"),
			}
		)
		frappe.set_user(self.operator)
		with self.assertRaises(frappe.PermissionError):
			archive_saved_report(
				{
					"saved_report": second["saved_report"],
					"idempotency_key": _key("archive-report-foreign"),
				}
			)

	def test_excel_export_is_server_side_and_oversize_is_rejected(self) -> None:
		frappe.set_user(self.manager)
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

		with patch.dict(
			PAGINATED_REPORT_LOADERS,
			{"FI01": lambda _payload: {"rows": [], "pagination": {"total": 5000}}},
		):
			_assert_export_size({}, "FI01")
		with patch.dict(
			PAGINATED_REPORT_LOADERS,
			{"FI01": lambda _payload: {"rows": [], "pagination": {"total": 5001}}},
		):
			with self.assertRaisesRegex(frappe.ValidationError, "supera el límite"):
				_assert_export_size({}, "FI01")

		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			export_report(
				{
					"report_code": "BI01",
					"format": "xlsx",
					"project": self.project,
				}
			)
