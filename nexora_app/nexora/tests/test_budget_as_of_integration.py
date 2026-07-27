from __future__ import annotations

import uuid
from decimal import Decimal

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.budget.service import activate_budget, amend_budget, create_budget
from nexora.dashboard.snapshot_query import get_executive_snapshot
from nexora.financial.operations import execute_financial_operation
from nexora.financial.sources import create_fund_source


def _key(prefix: str) -> str:
	return f"{prefix}-{uuid.uuid4().hex}"


def _user(email: str, role: str) -> str:
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


class TestBudgetAsOfMariaDB(FrappeTestCase):
	def setUp(self) -> None:
		super().setUp()
		frappe.set_user("Administrator")
		marker = uuid.uuid4().hex[:10]
		self.project = str(
			frappe.get_doc(
				{
					"doctype": "Project",
					"project_name": f"_Test NEXORA Budget As Of {marker}",
					"status": "Open",
				}
			).insert(ignore_permissions=True).name
		)
		self.operator = _user(
			f"nxr-budget-asof-operator-{marker}@example.test",
			"NEXORA Finance Operator",
		)
		self.manager = _user(
			f"nxr-budget-asof-manager-{marker}@example.test",
			"NEXORA Finance Manager",
		)
		today = frappe.utils.getdate(frappe.utils.today())
		self.budget_date = frappe.utils.add_days(today, -30).isoformat()
		self.outflow_date = frappe.utils.add_days(today, -20).isoformat()
		self.amendment_date = frappe.utils.add_days(today, -10).isoformat()
		self.before_outflow = frappe.utils.add_days(today, -25).isoformat()
		self.before_amendment = frappe.utils.add_days(today, -15).isoformat()
		self.after_amendment = frappe.utils.add_days(today, -5).isoformat()

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def test_pr02_uses_budget_version_and_effects_at_the_selected_cutoff(self) -> None:
		frappe.set_user(self.operator)
		source = create_fund_source(
			{
				"idempotency_key": _key("budget-asof-source"),
				"source_name": "Fuente para presupuesto histórico",
				"channel": "Remittance",
				"project": self.project,
				"source_date": self.budget_date,
				"currency": "HNL",
				"original_amount": 2000,
				"exchange_rate": 1,
				"origin_or_sender": "Prueba presupuesto histórico",
				"custodian": self.operator,
			}
		)["fund_source"]

		frappe.set_user(self.manager)
		budget = create_budget(
			{
				"idempotency_key": _key("budget-asof-v1"),
				"project": self.project,
				"title": "Presupuesto histórico v1",
				"effective_date": self.budget_date,
				"lines": [
					{
						"economic_category": "CONSTRUCTION_MATERIALS",
						"description": "Materiales v1",
						"approved_hnl": 1000,
					}
				],
			}
		)
		activate_budget({"budget": budget["budget"]})

		frappe.set_user(self.operator)
		execute_financial_operation(
			{
				"idempotency_key": _key("budget-asof-outflow"),
				"operation_type": "Outflow",
				"operation_date": self.outflow_date,
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
		amend_budget(
			{
				"idempotency_key": _key("budget-asof-v2"),
				"budget": budget["budget"],
				"title": "Presupuesto histórico v2",
				"effective_date": self.amendment_date,
				"lines": [
					{
						"economic_category": "CONSTRUCTION_MATERIALS",
						"description": "Materiales v2",
						"approved_hnl": 1500,
					}
				],
			}
		)

		frappe.set_user(self.operator)
		before_outflow = get_executive_snapshot(
			{"project": self.project, "to_date": self.before_outflow}
		)["budgets"]
		self.assertEqual(Decimal("1000.00"), Decimal(str(before_outflow["total_approved_hnl"])))
		self.assertEqual(Decimal("0.00"), Decimal(str(before_outflow["total_executed_hnl"])))
		self.assertEqual(Decimal("1000.00"), Decimal(str(before_outflow["total_available_hnl"])))

		before_amendment = get_executive_snapshot(
			{"project": self.project, "to_date": self.before_amendment}
		)["budgets"]
		self.assertEqual(Decimal("1000.00"), Decimal(str(before_amendment["total_approved_hnl"])))
		self.assertEqual(Decimal("200.00"), Decimal(str(before_amendment["total_executed_hnl"])))
		self.assertEqual(Decimal("800.00"), Decimal(str(before_amendment["total_available_hnl"])))

		after_amendment = get_executive_snapshot(
			{
				"project": self.project,
				"to_date": self.after_amendment,
				"economic_category": "CONSTRUCTION_MATERIALS",
			}
		)
		budgets = after_amendment["budgets"]
		self.assertEqual(Decimal("1500.00"), Decimal(str(budgets["total_approved_hnl"])))
		self.assertEqual(Decimal("200.00"), Decimal(str(budgets["total_executed_hnl"])))
		self.assertEqual(Decimal("1300.00"), Decimal(str(budgets["total_available_hnl"])))
		self.assertEqual(1, len(budgets["lines"]))
		self.assertEqual("CONSTRUCTION_MATERIALS", budgets["lines"][0]["category"])
		self.assertTrue(after_amendment["filter_context"]["budget_kpis_filtered"])
