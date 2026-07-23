from __future__ import annotations

import uuid
from decimal import Decimal

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.financial.analytics import (
	execute_central_operation,
	get_advance_status,
	list_analytic_catalogs,
	prepare_central_payload,
)
from nexora.financial.sources import create_fund_source, list_source_balances

test_dependencies = ["Project", "Cost Center"]


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


def _ensure_project(project_name: str) -> str:
	existing = frappe.db.get_value("Project", {"project_name": project_name}, "name")
	if existing:
		return str(existing)
	return str(
		frappe.get_doc({"doctype": "Project", "project_name": project_name, "status": "Open"})
		.insert(ignore_permissions=True)
		.name
	)


class TestCentralLedgerMariaDB(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.origin_project = _ensure_project("_Test Project")
		cls.target_project = _ensure_project("_Test Project 2")
		cls.cost_center = frappe.db.get_value("Cost Center", {"is_group": 0}, "name")
		if not cls.cost_center:
			raise AssertionError("Cost Center test dependency did not create a leaf cost center")
		cls.requester = _ensure_user("nxr-ledger-requester@example.test", "NEXORA Finance Operator")
		cls.executor = _ensure_user("nxr-ledger-executor@example.test", "NEXORA Finance Operator")
		cls.approver = _ensure_user("nxr-ledger-approver@example.test", "NEXORA Finance Manager")
		cls.correction_executor = _ensure_user("nxr-ledger-correction@example.test", "NEXORA Finance Manager")
		cls.responsible = _ensure_user("nxr-ledger-responsible@example.test", "NEXORA Project Viewer")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _source(self, project: str, amount: int) -> str:
		frappe.set_user(self.executor)
		return create_fund_source(
			{
				"idempotency_key": _key("ledger-source"),
				"source_name": f"Fuente libro {uuid.uuid4().hex[:8]}",
				"channel": "Cash",
				"project": project,
				"currency": "HNL",
				"original_amount": amount,
				"exchange_rate": 1,
				"origin_or_sender": "Prueba Libro Central",
				"custodian": self.executor,
			}
		)["fund_source"]

	def _balance(self, project: str, source: str) -> Decimal:
		frappe.set_user(self.executor)
		value = next(row for row in list_source_balances(project) if row["source"] == source)["balance_hnl"]
		return Decimal(value)

	def _outflow(self, source: str, amount: int, *, key: str | None = None) -> dict[str, object]:
		frappe.set_user(self.executor)
		return execute_central_operation(
			{
				"idempotency_key": key or _key("outflow"),
				"operation_code": "CONSTRUCTION_PAYMENT",
				"economic_category": "CONSTRUCTION_MATERIALS",
				"project": self.origin_project,
				"amount_hnl": amount,
				"allocations": [{"source": source, "amount_hnl": amount}],
				"cost_center": self.cost_center,
				"beneficiary_doctype": "User",
				"beneficiary": self.responsible,
				"requester": self.requester,
				"approved_by": self.approver,
			}
		)

	def _correction_payload(
		self,
		code: str,
		category: str,
		reference: str,
		amount: int,
		**extra: object,
	) -> dict[str, object]:
		return {
			"idempotency_key": _key(code.lower()),
			"operation_code": code,
			"economic_category": category,
			"project": self.origin_project,
			"reference_name": reference,
			"amount_hnl": amount,
			"requester": self.requester,
			"approved_by": self.approver,
			**extra,
		}

	def test_catalogs_are_seeded_and_maximum_account_is_savings_not_cost(self) -> None:
		frappe.set_user(self.approver)
		catalogs = list_analytic_catalogs()
		self.assertTrue(any(row["code"] == "MAXIMUM_ACCOUNT" for row in catalogs["operation_types"]))
		self.assertTrue(any(row["code"] == "MAXIMUM_ACCOUNT" for row in catalogs["economic_categories"]))
		source = self._source(self.origin_project, 500)
		frappe.set_user(self.executor)
		result = execute_central_operation(
			{
				"idempotency_key": _key("maximum"),
				"operation_code": "MAXIMUM_ACCOUNT",
				"economic_category": "MAXIMUM_ACCOUNT",
				"project": self.origin_project,
				"amount_hnl": 100,
				"allocations": [{"source": source, "amount_hnl": 100}],
				"requester": self.requester,
				"approved_by": self.approver,
			}
		)
		self.assertEqual(Decimal("400.00"), self._balance(self.origin_project, source))
		self.assertEqual(
			100,
			frappe.db.get_value(
				"NXR Operation Effect",
				{"operation": result["operation"], "dimension": "Savings"},
				"amount_hnl",
			),
		)
		self.assertFalse(
			frappe.db.exists("NXR Operation Effect", {"operation": result["operation"], "dimension": "Cost"})
		)

	def test_internal_transfer_is_atomic_net_zero_and_segregated(self) -> None:
		origin = self._source(self.origin_project, 500)
		destination = self._source(self.target_project, 50)
		frappe.set_user(self.executor)
		result = execute_central_operation(
			{
				"idempotency_key": _key("transfer"),
				"operation_code": "INTERNAL_TRANSFER",
				"economic_category": "INTERNAL_TRANSFER",
				"project": self.origin_project,
				"target_project": self.target_project,
				"destination_source": destination,
				"amount_hnl": 100,
				"allocations": [{"source": origin, "amount_hnl": 100}],
				"requester": self.requester,
				"approved_by": self.approver,
			}
		)
		self.assertEqual(Decimal("400.00"), self._balance(self.origin_project, origin))
		self.assertEqual(Decimal("150.00"), self._balance(self.target_project, destination))
		effects = frappe.get_all(
			"NXR Operation Effect",
			filters={"operation": result["operation"], "dimension": "Funds"},
			pluck="amount_hnl",
		)
		self.assertEqual(0, sum(effects))

	def test_reclassification_is_partial_balanced_idempotent_and_capped(self) -> None:
		source = self._source(self.origin_project, 1200)
		original = self._outflow(source, 1000)
		funds_after_original = self._balance(self.origin_project, source)
		key = _key("reclass")
		payload = self._correction_payload(
			"RECLASSIFICATION",
			"CONSTRUCTION_LABOR",
			str(original["operation"]),
			400,
			idempotency_key=key,
			cost_center=self.cost_center,
		)
		frappe.set_user(self.correction_executor)
		result = execute_central_operation(payload)
		self.assertEqual(result, execute_central_operation(payload))
		self.assertEqual(funds_after_original, self._balance(self.origin_project, source))
		self.assertFalse(
			frappe.db.exists("NXR Operation Effect", {"operation": result["operation"], "dimension": "Funds"})
		)
		rows = frappe.get_all(
			"NXR Operation Effect",
			filters={"operation": result["operation"]},
			fields=["dimension", "amount_hnl", "economic_category", "reverses_effect"],
		)
		for dimension in ("Cost", "Budget"):
			dimension_rows = [row for row in rows if row.dimension == dimension]
			self.assertEqual(0, sum(row.amount_hnl for row in dimension_rows))
			self.assertTrue(any(row.amount_hnl < 0 for row in dimension_rows))
			self.assertTrue(any(row.amount_hnl > 0 for row in dimension_rows))
			self.assertTrue(any(row.reverses_effect for row in dimension_rows if row.amount_hnl < 0))
		with self.assertRaisesRegex(frappe.ValidationError, "disponible"):
			execute_central_operation(
				{
					**payload,
					"idempotency_key": _key("reclass-excess"),
					"amount_hnl": 601,
				}
			)

	def test_real_return_tracks_source_relation_partial_duplicate_and_excess(self) -> None:
		original_source = self._source(self.origin_project, 1200)
		related_source = self._source(self.origin_project, 50)
		original = self._outflow(original_source, 1000)
		key = _key("return")
		payload = self._correction_payload(
			"REAL_RETURN",
			"RETURN",
			str(original["operation"]),
			300,
			idempotency_key=key,
			evidence="/private/files/return-300.pdf",
			allocations=[{"source": original_source, "amount_hnl": 300}],
		)
		frappe.set_user(self.correction_executor)
		first = execute_central_operation(payload)
		self.assertEqual(first, execute_central_operation(payload))
		self.assertEqual(Decimal("500.00"), self._balance(self.origin_project, original_source))
		frappe.set_user(self.correction_executor)
		second = execute_central_operation(
			{
				**payload,
				"idempotency_key": _key("return-related"),
				"amount_hnl": 200,
				"evidence": "/private/files/return-related.pdf",
				"allocations": [
					{
						"source": related_source,
						"original_source": original_source,
						"amount_hnl": 200,
					}
				],
			}
		)
		allocation = frappe.get_all(
			"NXR Fund Allocation",
			filters={"operation": second["operation"]},
			fields=["fund_source", "related_source"],
		)[0]
		self.assertEqual(related_source, allocation.fund_source)
		self.assertEqual(original_source, allocation.related_source)
		with self.assertRaisesRegex(frappe.ValidationError, "recuperable"):
			execute_central_operation(
				{
					**payload,
					"idempotency_key": _key("return-excess"),
					"amount_hnl": 501,
					"allocations": [{"source": original_source, "amount_hnl": 501}],
				}
			)

	def test_reversal_without_cash_is_derived_partial_idempotent_and_capped(self) -> None:
		source = self._source(self.origin_project, 1000)
		original = self._outflow(source, 800)
		funds_before = self._balance(self.origin_project, source)
		key = _key("reversal")
		payload = self._correction_payload(
			"REVERSAL_NO_CASH",
			"REVERSAL",
			str(original["operation"]),
			300,
			idempotency_key=key,
		)
		frappe.set_user(self.correction_executor)
		result = execute_central_operation(payload)
		self.assertEqual(result, execute_central_operation(payload))
		self.assertEqual(funds_before, self._balance(self.origin_project, source))
		self.assertFalse(
			frappe.db.exists("NXR Operation Effect", {"operation": result["operation"], "dimension": "Funds"})
		)
		rows = frappe.get_all(
			"NXR Operation Effect",
			filters={"operation": result["operation"]},
			fields=["amount_hnl", "project", "cost_center", "reverses_effect"],
		)
		self.assertTrue(all(row.amount_hnl < 0 for row in rows))
		self.assertTrue(all(row.project == self.origin_project for row in rows))
		self.assertTrue(all(row.cost_center == self.cost_center for row in rows))
		self.assertTrue(all(row.reverses_effect for row in rows))
		with self.assertRaisesRegex(frappe.ValidationError, "disponible"):
			execute_central_operation(
				{
					**payload,
					"idempotency_key": _key("reversal-excess"),
					"amount_hnl": 501,
				}
			)

	def test_advance_status_settlement_and_no_double_fund_consumption(self) -> None:
		source = self._source(self.origin_project, 1500)
		frappe.set_user(self.executor)
		advance = execute_central_operation(
			{
				"idempotency_key": _key("advance"),
				"operation_code": "ADVANCE_DISBURSEMENT",
				"economic_category": "ADVANCE",
				"project": self.origin_project,
				"amount_hnl": 1000,
				"allocations": [{"source": source, "amount_hnl": 1000}],
				"beneficiary_doctype": "User",
				"beneficiary": self.responsible,
				"operation_date": "2026-07-22",
				"due_date": "2026-08-22",
				"requester": self.requester,
				"approved_by": self.approver,
			}
		)
		funds_after_advance = self._balance(self.origin_project, source)
		key = _key("settlement")
		payload = self._correction_payload(
			"ADVANCE_SETTLEMENT",
			"CONSTRUCTION_MATERIALS",
			str(advance["operation"]),
			400,
			idempotency_key=key,
			cost_center=self.cost_center,
		)
		frappe.set_user(self.correction_executor)
		settlement = execute_central_operation(payload)
		self.assertEqual(settlement, execute_central_operation(payload))
		self.assertEqual(funds_after_advance, self._balance(self.origin_project, source))
		self.assertFalse(
			frappe.db.exists(
				"NXR Operation Effect",
				{"operation": settlement["operation"], "dimension": "Funds"},
			)
		)
		self.assertEqual(
			400,
			frappe.db.get_value(
				"NXR Operation Effect",
				{"operation": settlement["operation"], "dimension": "Cost"},
				"amount_hnl",
			),
		)
		self.assertFalse(
			frappe.db.exists(
				"NXR Operation Effect",
				{"operation": settlement["operation"], "dimension": "Budget"},
			)
		)
		status = get_advance_status(str(advance["operation"]))
		self.assertEqual("1000.00", status["total_disbursed_hnl"])
		self.assertEqual("400.00", status["total_settled_hnl"])
		self.assertEqual("600.00", status["outstanding_hnl"])
		self.assertEqual(self.responsible, status["beneficiary"])
		self.assertEqual("2026-08-22", str(status["due_date"]))
		with self.assertRaisesRegex(frappe.ValidationError, "supera"):
			execute_central_operation(
				{
					**payload,
					"idempotency_key": _key("settlement-excess"),
					"amount_hnl": 601,
				}
			)

	def test_document_substitution_is_zero_value_idempotent_and_unique(self) -> None:
		source = self._source(self.origin_project, 500)
		original = self._outflow(source, 200)
		funds_before = self._balance(self.origin_project, source)
		key = _key("substitution")
		payload = self._correction_payload(
			"DOCUMENT_SUBSTITUTION",
			"DOCUMENTARY",
			str(original["operation"]),
			0,
			idempotency_key=key,
			evidence="/private/files/substitution.pdf",
		)
		frappe.set_user(self.correction_executor)
		result = execute_central_operation(payload)
		self.assertEqual(result, execute_central_operation(payload))
		self.assertEqual(funds_before, self._balance(self.origin_project, source))
		self.assertFalse(frappe.db.exists("NXR Operation Effect", {"operation": result["operation"]}))
		with self.assertRaisesRegex(frappe.ValidationError, "ya tiene una sustitución"):
			execute_central_operation(
				{
					**payload,
					"idempotency_key": _key("substitution-duplicate"),
					"evidence": "/private/files/substitution-2.pdf",
				}
			)

	def test_server_side_segregation_rejects_every_required_operation_family(self) -> None:
		frappe.set_user(self.correction_executor)
		common = {
			"project": self.origin_project,
			"amount_hnl": 100,
			"requester": self.correction_executor,
			"approved_by": self.approver,
		}
		cases = [
			{
				**common,
				"operation_code": "INTERNAL_TRANSFER",
				"economic_category": "INTERNAL_TRANSFER",
				"target_project": self.target_project,
				"destination_source": "MISSING",
			},
			{
				**common,
				"operation_code": "ADVANCE_DISBURSEMENT",
				"economic_category": "ADVANCE",
				"beneficiary": self.responsible,
				"operation_date": "2026-07-22",
				"due_date": "2026-08-22",
			},
			{
				**common,
				"operation_code": "ADVANCE_SETTLEMENT",
				"economic_category": "ADVANCE_SETTLEMENT",
				"reference_name": "MISSING",
				"cost_center": self.cost_center,
			},
			{
				**common,
				"operation_code": "RECLASSIFICATION",
				"economic_category": "CONSTRUCTION_LABOR",
				"reference_name": "MISSING",
			},
			{
				**common,
				"operation_code": "REAL_RETURN",
				"economic_category": "RETURN",
				"reference_name": "MISSING",
				"evidence": "/private/files/return.pdf",
			},
			{
				**common,
				"operation_code": "REVERSAL_NO_CASH",
				"economic_category": "REVERSAL",
				"reference_name": "MISSING",
			},
			{
				**common,
				"operation_code": "DOCUMENT_SUBSTITUTION",
				"economic_category": "DOCUMENTARY",
				"reference_name": "MISSING",
				"amount_hnl": 0,
				"evidence": "/private/files/substitution.pdf",
			},
		]
		for payload in cases:
			with self.subTest(operation_code=payload["operation_code"]):
				with self.assertRaisesRegex(frappe.ValidationError, "tres usuarios distintos"):
					prepare_central_payload(payload)


if __name__ == "__main__":
	import unittest

	unittest.main()
