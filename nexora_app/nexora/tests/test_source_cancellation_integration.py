from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.financial.operations import execute_financial_operation, preview_financial_operation
from nexora.financial.sources import cancel_fund_source, create_fund_source


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


class TestSourceCancellationMariaDB(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.project = _ensure_project("_Test Cancellation Project")
		cls.operator = _ensure_user("nxr-cancel-operator@example.test", "NEXORA Finance Operator")
		cls.manager = _ensure_user("nxr-cancel-manager@example.test", "NEXORA Finance Manager")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _source(self, amount=1000):
		frappe.set_user(self.operator)
		return create_fund_source(
			{
				"idempotency_key": _key("cancel-source"),
				"source_name": f"Ingreso anulable {uuid.uuid4().hex[:8]}",
				"channel": "Cash",
				"project": self.project,
				"currency": "HNL",
				"original_amount": amount,
				"exchange_rate": 1,
				"origin_or_sender": "Prueba de anulación",
				"custodian": self.operator,
			}
		)

	def test_manager_cancels_unused_income_with_compensating_effect(self):
		created = self._source(1250)
		frappe.set_user(self.manager)
		result = cancel_fund_source(
			created["fund_source"],
			"Monto registrado por error durante la prueba.",
			_key("cancel"),
		)

		self.assertEqual("Cancelled", result["status"])
		self.assertEqual(
			"Cancelled", frappe.db.get_value("NXR Fund Source", created["fund_source"], "status")
		)
		self.assertEqual(
			"Compensated Total", frappe.db.get_value("NXR Operation", created["operation"], "status")
		)
		effects = frappe.get_all(
			"NXR Operation Effect",
			filters={"fund_source": created["fund_source"]},
			fields=["effect_type", "amount_hnl", "is_reversal", "reverses_effect"],
			order_by="creation asc",
		)
		self.assertEqual(2, len(effects))
		self.assertEqual("Received", effects[0].effect_type)
		self.assertEqual("Reversed", effects[1].effect_type)
		self.assertEqual(-1250, float(effects[1].amount_hnl))
		self.assertEqual(1, effects[1].is_reversal)
		self.assertEqual(frappe.db.get_value("NXR Operation Effect", {"operation": created["operation"]}), effects[1].reverses_effect)

	def test_income_with_related_outflow_cannot_be_cancelled(self):
		created = self._source(1000)
		payload = {
			"idempotency_key": _key("cancel-outflow"),
			"operation_type": "Outflow",
			"project": self.project,
			"amount_hnl": 100,
			"allocations": [{"source": created["fund_source"], "amount_hnl": 100}],
			"requester": self.operator,
			"approved_by": self.manager,
		}
		frappe.set_user(self.operator)
		payload["preview_hash"] = preview_financial_operation(payload)["preview_hash"]
		execute_financial_operation(payload)

		frappe.set_user(self.manager)
		with self.assertRaisesRegex(frappe.ValidationError, "movimientos relacionados"):
			cancel_fund_source(
				created["fund_source"],
				"El ingreso ya fue utilizado y no debe anularse.",
				_key("cancel-used"),
			)
		self.assertEqual(
			"Active", frappe.db.get_value("NXR Fund Source", created["fund_source"], "status")
		)

	def test_operator_cannot_cancel_income(self):
		created = self._source(500)
		frappe.set_user(self.operator)
		with self.assertRaises(frappe.PermissionError):
			cancel_fund_source(
				created["fund_source"],
				"El operador no puede aprobar esta anulación.",
				_key("cancel-denied"),
			)
