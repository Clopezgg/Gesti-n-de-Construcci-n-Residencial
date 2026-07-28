from __future__ import annotations

import base64
import json
import uuid
from decimal import Decimal

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.file_manager import save_file

from nexora.budget.service import activate_budget, create_budget
from nexora.dashboard.executive import get_executive_snapshot
from nexora.dashboard.service import get_dashboard_summary
from nexora.financial.commitments import create_commitment
from nexora.financial.evidence import register_evidence, review_evidence
from nexora.financial.operations import execute_financial_operation
from nexora.financial.sources import cancel_fund_source, create_fund_source
from nexora.progress.service import create_progress_record, transition_progress_record

PNG_1X1 = base64.b64decode(
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
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
	elif not frappe.db.exists("Has Role", {"parent": email, "role": role}):
		user = frappe.get_doc("User", email)
		user.append("roles", {"role": role})
		user.save(ignore_permissions=True)
	return email


class TestDashboardMariaDB(FrappeTestCase):
	def setUp(self) -> None:
		super().setUp()
		frappe.set_user("Administrator")
		marker = uuid.uuid4().hex[:10]
		self.project = str(
			frappe.get_doc(
				{
					"doctype": "Project",
					"project_name": f"_Test NEXORA Dashboard {marker}",
					"status": "Open",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		self.operator = _ensure_user(
			f"nxr-dashboard-operator-{marker}@example.test",
			"NEXORA Finance Operator",
		)
		self.manager = _ensure_user(
			f"nxr-dashboard-manager-{marker}@example.test",
			"NEXORA Finance Manager",
		)
		self.viewer = _ensure_user(
			f"nxr-dashboard-viewer-{marker}@example.test",
			"NEXORA Project Viewer",
		)

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def test_dashboard_allows_viewer_and_rejects_guest(self) -> None:
		frappe.set_user(self.viewer)
		summary = get_dashboard_summary({"project": self.project})
		self.assertEqual(self.project, summary["context"]["project"])
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			get_dashboard_summary({"project": self.project})
		with self.assertRaises(frappe.PermissionError):
			get_executive_snapshot({"project": self.project})

	def test_recent_operations_use_business_semantics_and_project_scope(self) -> None:
		frappe.set_user(self.operator)
		active = create_fund_source(
			{
				"idempotency_key": _key("dashboard-active-transfer"),
				"source_name": "Transferencia activa",
				"channel": "Transfer",
				"project": self.project,
				"currency": "HNL",
				"original_amount": 100,
				"exchange_rate": 1,
				"origin_or_sender": "Prueba visual",
				"custodian": self.operator,
				"institution": "Banco de prueba",
				"account_reference": "001-TRANSFER",
				"external_reference": "TRX-ACTIVA",
			}
		)
		cancelled = create_fund_source(
			{
				"idempotency_key": _key("dashboard-cancelled-deposit"),
				"source_name": "Depósito por anular",
				"channel": "Deposit",
				"project": self.project,
				"currency": "HNL",
				"original_amount": 80,
				"exchange_rate": 1,
				"origin_or_sender": "Prueba visual",
				"custodian": self.operator,
				"institution": "Banco de prueba",
				"account_reference": "002-DEPOSIT",
				"external_reference": "DEP-ANULADO",
			}
		)
		cancellation = cancel_fund_source(
			str(cancelled["fund_source"]),
			"Ingreso duplicado registrado para validar la presentación.",
			_key("dashboard-cancel-source"),
		)

		other_project = str(
			frappe.get_doc(
				{
					"doctype": "Project",
					"project_name": f"_Test NEXORA Dashboard Other {uuid.uuid4().hex[:8]}",
					"status": "Open",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		outside = create_fund_source(
			{
				"idempotency_key": _key("dashboard-other-project"),
				"source_name": "Efectivo de otro proyecto",
				"channel": "Cash",
				"project": other_project,
				"currency": "HNL",
				"original_amount": 50,
				"exchange_rate": 1,
				"origin_or_sender": "Proyecto ajeno",
				"custodian": self.operator,
			}
		)

		today = frappe.utils.today()
		snapshot = get_executive_snapshot(
			{"project": self.project, "from_date": today, "to_date": today}
		)
		rows = {str(row["name"]): row for row in snapshot["recent_operations"]}
		self.assertNotIn(str(outside["operation"]), rows)

		active_row = rows[str(active["operation"])]
		self.assertEqual("Income", active_row["presentation_kind"])
		self.assertEqual("Posted", active_row["presentation_status"])
		self.assertEqual("income", active_row["presentation_tone"])
		self.assertFalse(active_row["presentation_struck"])
		self.assertEqual("Transfer", active_row["source_channel"])

		original_row = rows[str(cancelled["operation"])]
		self.assertEqual("Compensated Total", original_row["status"])
		self.assertEqual("Income", original_row["presentation_kind"])
		self.assertEqual("Posted", original_row["presentation_status"])
		self.assertEqual("voided", original_row["presentation_tone"])
		self.assertTrue(original_row["presentation_struck"])
		self.assertEqual("Deposit", original_row["source_channel"])

		reversal_row = rows[str(cancellation["reversal_operation"])]
		self.assertEqual("Analytic Adjustment", reversal_row["operation_type"])
		self.assertEqual("Cancellation", reversal_row["presentation_kind"])
		self.assertEqual("Posted", reversal_row["presentation_status"])
		self.assertEqual("voided", reversal_row["presentation_tone"])
		self.assertTrue(reversal_row["presentation_struck"])
		self.assertEqual("Deposit", reversal_row["source_channel"])

	def test_dashboard_reconciles_ledger_budget_accounts_progress_and_evidence(self) -> None:
		self.assertEqual("nexora-dashboard", frappe.db.get_default("desktop:home_page"))
		frappe.set_user(self.operator)
		source = str(
			create_fund_source(
				{
					"idempotency_key": _key("dashboard-source"),
					"source_name": "Remesa para dashboard",
					"channel": "Remittance",
					"project": self.project,
					"currency": "HNL",
					"original_amount": 1000,
					"exchange_rate": 1,
					"origin_or_sender": "Prueba dashboard",
					"custodian": self.operator,
				}
			)["fund_source"]
		)
		execute_financial_operation(
			{
				"idempotency_key": _key("dashboard-outflow"),
				"operation_type": "Outflow",
				"project": self.project,
				"amount_hnl": 200,
				"allocations": [{"source": source, "amount_hnl": 200}],
				"economic_category": "CONSTRUCTION_MATERIALS",
				"affects_budget": 1,
				"requester": self.operator,
				"approved_by": self.manager,
			}
		)

		frappe.set_user(self.manager)
		budget = create_budget(
			{
				"idempotency_key": _key("dashboard-budget"),
				"project": self.project,
				"title": "Presupuesto operativo",
				"lines": [
					{
						"economic_category": "CONSTRUCTION_MATERIALS",
						"description": "Materiales",
						"approved_hnl": 1500,
					}
				],
			}
		)
		activate_budget({"budget": budget["budget"]})
		create_commitment(
			{
				"idempotency_key": _key("dashboard-commitment"),
				"project": self.project,
				"amount_hnl": 300,
				"allocations": [{"source": source, "amount_hnl": 300}],
				"economic_category": "CONSTRUCTION_MATERIALS",
				"affects_budget": 1,
				"requester": self.operator,
				"approved_by": self.manager,
				"description": "Pago de materiales pendiente",
				"expiry_date": frappe.utils.add_days(frappe.utils.today(), 10),
			}
		)

		frappe.set_user(self.operator)
		file_doc = save_file(
			f"dashboard-{uuid.uuid4().hex}.png",
			PNG_1X1,
			None,
			None,
			is_private=1,
		)
		evidence = register_evidence(
			{
				"project": self.project,
				"evidence_kind": "Other",
				"channel": "Other",
				"file_url": file_doc.file_url,
				"external_reference": "DASHBOARD-INTEGRATION",
				"idempotency_key": _key("dashboard-evidence"),
			}
		)
		frappe.set_user(self.manager)
		review_evidence(str(evidence["evidence"]), "Validated", _key("dashboard-evidence-review"))
		progress = create_progress_record(
			{
				"project": self.project,
				"phase": "Cimentación",
				"description": "Avance físico comprobado",
				"progress_percent": 42,
				"recorded_date": frappe.utils.today(),
				"photos": json.dumps([file_doc.file_url]),
				"idempotency_key": _key("dashboard-progress"),
			}
		)
		transition_progress_record({"record": progress["name"], "target_status": "Submitted"})
		transition_progress_record({"record": progress["name"], "target_status": "Approved"})

		summary = get_dashboard_summary({"project": self.project})
		self.assertEqual(self.project, summary["context"]["project"])
		self.assertEqual(Decimal("800.00"), Decimal(str(summary["finance"]["total_balance_hnl"])))
		self.assertEqual(Decimal("300.00"), Decimal(str(summary["finance"]["total_reserved_hnl"])))
		self.assertEqual(Decimal("500.00"), Decimal(str(summary["finance"]["total_available_hnl"])))
		self.assertEqual(Decimal("1000.00"), Decimal(str(summary["finance"]["inflows_hnl"])))
		self.assertEqual(Decimal("200.00"), Decimal(str(summary["finance"]["outflows_hnl"])))

		self.assertEqual(Decimal("1500.00"), Decimal(str(summary["budgets"]["total_approved_hnl"])))
		self.assertEqual(Decimal("300.00"), Decimal(str(summary["budgets"]["total_committed_hnl"])))
		self.assertEqual(Decimal("200.00"), Decimal(str(summary["budgets"]["total_executed_hnl"])))
		self.assertEqual(Decimal("1000.00"), Decimal(str(summary["budgets"]["total_available_hnl"])))
		self.assertEqual(33.33, summary["budgets"]["utilization_percent"])

		self.assertEqual(1, summary["pending_accounts"]["count"])
		self.assertEqual(Decimal("300.00"), Decimal(str(summary["pending_accounts"]["total_hnl"])))
		self.assertEqual(1, len(summary["pending_accounts"]["upcoming"]))
		self.assertEqual(Decimal("42.00"), Decimal(str(summary["progress"]["physical_percent"])))
		self.assertEqual([file_doc.file_url], summary["progress"]["photos"])
		self.assertEqual(1, summary["evidence"]["count"])
		self.assertEqual("Validated", summary["evidence"]["items"][0]["status"])
		self.assertGreaterEqual(len(summary["recent_operations"]), 3)
