from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.financial.commitments import create_commitment, execute_commitment, release_commitment
from nexora.financial.operations import execute_financial_operation, preview_financial_operation
from nexora.financial.sources import create_fund_source, list_source_balances

test_dependencies = ["Project"]


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


class TestNexoraFinancialMariaDB(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.project = "_Test Project"
		cls.requester = _ensure_user("nxr-requester@example.test", "NEXORA Finance Operator")
		cls.executor = _ensure_user("nxr-executor@example.test", "NEXORA Finance Operator")
		cls.manager = _ensure_user("nxr-manager@example.test", "NEXORA Finance Manager")
		cls.return_executor = _ensure_user("nxr-return@example.test", "NEXORA Administrator")
		cls.auditor = _ensure_user("nxr-auditor@example.test", "NEXORA Auditor")

	def tearDown(self) -> None:
		frappe.flags.nexora_fail_after_allocation = None
		frappe.set_user("Administrator")
		super().tearDown()

	def _source(
		self,
		amount,
		*,
		channel="Remittance",
		currency="HNL",
		exchange_rate=1,
		institution=None,
		account=None,
		reference=None,
	):
		frappe.set_user(self.executor)
		return create_fund_source(
			{
				"idempotency_key": _key("source"),
				"source_name": f"Fuente CI {uuid.uuid4().hex[:8]}",
				"channel": channel,
				"project": self.project,
				"currency": currency,
				"original_amount": amount,
				"exchange_rate": exchange_rate,
				"origin_or_sender": "Remitente CI",
				"custodian": self.executor,
				"institution": institution,
				"account_reference": account,
				"external_reference": reference,
			}
		)

	def _outflow(self, allocations, amount, key=None):
		return {
			"idempotency_key": key or _key("outflow"),
			"operation_type": "Outflow",
			"project": self.project,
			"amount_hnl": amount,
			"allocations": allocations,
			"requester": self.requester,
			"approved_by": self.manager,
		}

	def _balances(self, *sources):
		frappe.set_user(self.executor)
		wanted = set(sources)
		return {row["source"]: row for row in list_source_balances(self.project) if row["source"] in wanted}

	def test_direct_canonical_source_creation_is_rejected(self):
		frappe.set_user(self.executor)
		with self.assertRaisesRegex(frappe.ValidationError, "servicio transaccional NEXORA"):
			frappe.get_doc(
				{
					"doctype": "NXR Fund Source",
					"source_code": f"DIRECT-{uuid.uuid4().hex[:8]}",
					"source_name": "Fuente directa prohibida",
					"channel": "Cash",
					"project": self.project,
					"source_date": frappe.utils.today(),
					"currency": "HNL",
					"original_amount": 100,
					"exchange_rate": 1,
					"origin_or_sender": "Intento directo",
					"custodian": self.executor,
					"status": "Active",
				}
			).insert(ignore_permissions=True)

	def test_source_creation_hnl_fx_cash_and_transfer_validation(self):
		hnl = self._source(1000)
		self.assertEqual("1000.00", hnl["amount_hnl"])
		self.assertRegex(hnl["source_number"], r"^\d{12}$")
		self.assertEqual(
			"2450.00", self._source(100, currency="USD", exchange_rate="24.500000000")["amount_hnl"]
		)
		self.assertEqual("500.00", self._source(500, channel="Cash")["amount_hnl"])
		with self.assertRaisesRegex(frappe.ValidationError, "referencia"):
			self._source(500, channel="Transfer", institution="Banco CI", account="123")

	def test_atomic_multisource_idempotency_and_payload_conflict(self):
		first = self._source(6000)["fund_source"]
		second = self._source(4000)["fund_source"]
		payload = self._outflow(
			[{"source": first, "amount_hnl": 6000}, {"source": second, "amount_hnl": 4000}],
			10000,
			_key("multi"),
		)
		frappe.set_user(self.executor)
		payload["preview_hash"] = preview_financial_operation(payload)["preview_hash"]
		result = execute_financial_operation(payload)
		self.assertEqual(result, execute_financial_operation(payload))
		self.assertRegex(result["document_number"], r"^\d{12}$")
		self.assertEqual(2, frappe.db.count("NXR Fund Allocation", {"operation": result["operation"]}))
		balances = self._balances(first, second)
		self.assertEqual("0.00", balances[first]["balance_hnl"])
		self.assertEqual("0.00", balances[second]["balance_hnl"])
		changed = dict(payload)
		changed["amount_hnl"] = 9999
		with self.assertRaisesRegex(frappe.ValidationError, "payload diferente"):
			execute_financial_operation(changed)

	def test_mismatch_and_overdraw_are_rejected_without_partial_effects(self):
		source = self._source(1000)["fund_source"]
		frappe.set_user(self.executor)
		with self.assertRaisesRegex(frappe.ValidationError, "asignaciones suman"):
			execute_financial_operation(self._outflow([{"source": source, "amount_hnl": 900}], 1000))
		with self.assertRaisesRegex(frappe.ValidationError, "disponible suficiente"):
			execute_financial_operation(self._outflow([{"source": source, "amount_hnl": 1001}], 1001))
		balance = self._balances(source)[source]
		self.assertEqual("1000.00", balance["balance_hnl"])
		self.assertEqual("0.00", balance["reserved_hnl"])

	def test_second_allocation_failure_rolls_back_all_documents(self):
		first = self._source(6000)["fund_source"]
		second = self._source(4000)["fund_source"]
		key = _key("rollback")
		before = frappe.db.count("NXR Operation Effect")
		frappe.set_user(self.executor)
		frappe.flags.nexora_fail_after_allocation = 2
		with self.assertRaisesRegex(frappe.ValidationError, "asignación 2"):
			execute_financial_operation(
				self._outflow(
					[{"source": first, "amount_hnl": 6000}, {"source": second, "amount_hnl": 4000}],
					10000,
					key,
				)
			)
		frappe.flags.nexora_fail_after_allocation = None
		self.assertFalse(frappe.db.exists("NXR Idempotency Record", key))
		self.assertFalse(frappe.db.exists("NXR Operation", {"idempotency_key": key}))
		self.assertEqual(before, frappe.db.count("NXR Operation Effect"))
		balances = self._balances(first, second)
		self.assertEqual("6000.00", balances[first]["balance_hnl"])
		self.assertEqual("4000.00", balances[second]["balance_hnl"])

	def test_commitment_reserve_execute_and_release_without_double_consumption(self):
		source = self._source(1000)["fund_source"]
		reserve = {
			"idempotency_key": _key("commit"),
			"project": self.project,
			"amount_hnl": 400,
			"allocations": [{"source": source, "amount_hnl": 400}],
			"requester": self.requester,
			"approved_by": self.manager,
			"description": "Reserva CI",
		}
		frappe.set_user(self.manager)
		commitment = create_commitment(reserve)
		balance = self._balances(source)[source]
		self.assertEqual(
			("1000.00", "400.00", "600.00"),
			(balance["balance_hnl"], balance["reserved_hnl"], balance["available_hnl"]),
		)
		execution = {
			"idempotency_key": _key("commit-execute"),
			"commitment": commitment["commitment"],
			"amount_hnl": 200,
			"allocations": [{"source": source, "amount_hnl": 200}],
			"requester": self.requester,
			"approved_by": self.manager,
		}
		frappe.set_user(self.executor)
		execute_commitment(execution)
		balance = self._balances(source)[source]
		self.assertEqual(
			("800.00", "200.00", "600.00"),
			(balance["balance_hnl"], balance["reserved_hnl"], balance["available_hnl"]),
		)
		release = {**execution, "idempotency_key": _key("commit-release")}
		frappe.set_user(self.manager)
		release_commitment(release)
		balance = self._balances(source)[source]
		self.assertEqual(
			("800.00", "0.00", "800.00"),
			(balance["balance_hnl"], balance["reserved_hnl"], balance["available_hnl"]),
		)

	def test_reclassification_and_real_return(self):
		source = self._source(1000)["fund_source"]
		frappe.set_user(self.executor)
		execute_financial_operation(self._outflow([{"source": source, "amount_hnl": 400}], 400))
		frappe.set_user(self.manager)
		execute_financial_operation(
			{
				"idempotency_key": _key("reclass"),
				"operation_type": "Reclassification",
				"project": self.project,
				"amount_hnl": 0,
				"allocations": [],
			}
		)
		self.assertEqual("600.00", self._balances(source)[source]["balance_hnl"])
		frappe.set_user(self.return_executor)
		payload = {
			"idempotency_key": _key("return-missing"),
			"operation_type": "Real Return",
			"project": self.project,
			"amount_hnl": 100,
			"allocations": [{"source": source, "amount_hnl": 100}],
			"requester": self.requester,
			"approved_by": self.manager,
		}
		with self.assertRaisesRegex(frappe.ValidationError, "evidencia"):
			execute_financial_operation(payload)
		payload["idempotency_key"] = _key("return")
		payload["evidence"] = "/private/files/return-ci.pdf"
		execute_financial_operation(payload)
		self.assertEqual("700.00", self._balances(source)[source]["balance_hnl"])

	def test_auditor_cannot_execute_and_denial_writes_nothing(self):
		source = self._source(1000)["fund_source"]
		payload = self._outflow([{"source": source, "amount_hnl": 100}], 100)
		before = frappe.db.count("NXR Operation")
		frappe.set_user(self.auditor)
		with self.assertRaises(frappe.PermissionError):
			execute_financial_operation(payload)
		frappe.set_user(self.executor)
		self.assertEqual(before, frappe.db.count("NXR Operation"))
		self.assertEqual("1000.00", self._balances(source)[source]["balance_hnl"])

	def test_sequence_is_global_unique_and_twelve_digits(self):
		self._source(10)
		values = frappe.get_all("NXR Document Sequence", pluck="number")
		self.assertEqual(len(values), len(set(values)))
		self.assertTrue(values)
		self.assertTrue(all(len(v) == 12 and v.isdigit() for v in values))
