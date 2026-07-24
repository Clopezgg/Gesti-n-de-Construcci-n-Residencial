from __future__ import annotations

import uuid
from decimal import Decimal

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.file_manager import save_file

from nexora.contracts.service import (
	correct_contract_transaction,
	create_contract,
	create_contract_amendment,
	create_contract_estimate,
	create_contractor_profile,
	disburse_contract_advance,
	execute_contract_estimate_payment,
	get_contract,
	return_contract_retention,
	transition_contract,
	transition_contract_amendment,
	transition_contract_estimate,
	transition_contractor_profile,
)
from nexora.directory.service import consolidate_entities, create_entity, transition_entity
from nexora.financial.evidence import register_evidence, review_evidence
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


def _ensure_project() -> str:
	name = frappe.db.get_value("Project", {"project_name": "_Test NEXORA Contract Project"}, "name")
	if name:
		return str(name)
	return str(
		frappe.get_doc(
			{"doctype": "Project", "project_name": "_Test NEXORA Contract Project", "status": "Open"}
		)
		.insert(ignore_permissions=True)
		.name
	)


class TestContractMariaDB(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.project = _ensure_project()
		cls.cost_center = frappe.db.get_value("Cost Center", {"is_group": 0}, "name")
		if not cls.cost_center:
			raise AssertionError("Cost Center test dependency did not create a leaf cost center")
		cls.operator = _ensure_user("nxr-contract-operator@example.test", "NEXORA Finance Operator")
		cls.manager = _ensure_user("nxr-contract-manager@example.test", "NEXORA Finance Manager")
		cls.executor = _ensure_user("nxr-contract-executor@example.test", "NEXORA Administrator")
		cls.viewer = _ensure_user("nxr-contract-viewer@example.test", "NEXORA Project Viewer")

	def tearDown(self) -> None:
		frappe.flags.nexora_fail_after_allocation = None
		frappe.set_user("Administrator")
		super().tearDown()

	def _private_file(self, prefix: str, content: bytes) -> str:
		file_doc = save_file(
			f"{prefix}-{uuid.uuid4().hex}.txt", content, "Project", self.project, is_private=1
		)
		return str(file_doc.file_url)

	def _evidence(self, kind: str = "Other", channel: str = "Other") -> str:
		frappe.set_user(self.operator)
		registered = register_evidence(
			{
				"project": self.project,
				"evidence_kind": kind,
				"channel": channel,
				"file_url": self._private_file("contract-evidence", b"NEXORA CONTRACT EVIDENCE"),
				"external_reference": f"CONTRACT-{uuid.uuid4().hex[:10]}",
				"idempotency_key": _key("contract-evidence"),
			}
		)
		frappe.set_user(self.manager)
		review_evidence(str(registered["evidence"]), "Validated", _key("contract-evidence-review"))
		return str(registered["evidence"])

	def _entity(self, name: str) -> str:
		frappe.set_user(self.operator)
		created = create_entity(
			{
				"entity_type": "Organization",
				"display_name": f"{name} {uuid.uuid4().hex[:8]}",
				"identifiers": [
					{
						"identifier_type": "Internal Code",
						"identifier_value": f"{name}-{uuid.uuid4().hex}",
						"is_primary": 1,
					}
				],
				"idempotency_key": _key("contract-entity"),
			}
		)
		frappe.set_user(self.manager)
		transition_entity(str(created["name"]), "Active", _key("contract-entity-active"))
		return str(created["name"])

	def _profile(self, entity: str) -> str:
		frappe.set_user(self.manager)
		profile = create_contractor_profile(
			{
				"entity": entity,
				"classification": "Company",
				"valid_from": "2026-01-01",
				"valid_until": "2027-12-31",
				"compliance_status": "Valid",
				"idempotency_key": _key("contract-profile"),
			}
		)
		transition_contractor_profile(str(profile["profile"]), "Active", _key("contract-profile-active"))
		return str(profile["profile"])

	def _source(self, amount: int = 10000) -> str:
		frappe.set_user(self.operator)
		return str(
			create_fund_source(
				{
					"idempotency_key": _key("contract-source"),
					"source_name": f"Fuente contractual {uuid.uuid4().hex[:8]}",
					"channel": "Cash",
					"project": self.project,
					"currency": "HNL",
					"original_amount": amount,
					"exchange_rate": 1,
					"origin_or_sender": "Prueba contractual NEXORA",
					"custodian": self.operator,
				}
			)["fund_source"]
		)

	def _contract(self, labor: int = 1000, materials: int = 500) -> tuple[str, str, str, str]:
		entity = self._entity("Contratista")
		profile = self._profile(entity)
		source = self._source()
		document = self._evidence()
		lines = []
		if labor:
			lines.append(
				{
					"line_code": "LAB-001",
					"description": "Mano de obra",
					"cost_kind": "Labor",
					"cost_center": self.cost_center,
					"fund_source": source,
					"unit": "Contrato",
					"quantity": 1,
					"unit_rate": labor,
					"amount": labor,
				}
			)
		if materials:
			lines.append(
				{
					"line_code": "MAT-001",
					"description": "Materiales",
					"cost_kind": "Materials",
					"cost_center": self.cost_center,
					"fund_source": source,
					"unit": "Contrato",
					"quantity": 1,
					"unit_rate": materials,
					"amount": materials,
				}
			)
		frappe.set_user(self.operator)
		created = create_contract(
			{
				"contractor": entity,
				"contractor_profile": profile,
				"modality": "Unit Price",
				"project": self.project,
				"cost_center": self.cost_center,
				"fund_source": source,
				"responsible": self.viewer,
				"scope": "Construcción demostrativa controlada",
				"currency": "HNL",
				"exchange_rate": 1,
				"start_date": "2026-01-01",
				"end_date": "2026-12-31",
				"signed_on": "2026-01-01",
				"owner_signatory": "Propietaria",
				"contractor_signatory": "Contratista",
				"lines": lines,
				"evidence_rows": [
					{"evidence_type": "Contract", "evidence": document},
					{"evidence_type": "Signature", "evidence": document},
					{"evidence_type": "Approval", "evidence": document},
				],
				"idempotency_key": _key("contract-create"),
			}
		)
		contract = str(created["contract"])
		frappe.set_user(self.manager)
		for status in ("In Review", "Approved", "Active"):
			transition_contract(contract, status, _key(f"contract-{status}"))
		return contract, entity, profile, source

	def _estimate(
		self,
		contract: str,
		amount: int,
		*,
		advance: int = 0,
		retention: int = 0,
		fine: int = 0,
		deduction: int = 0,
	) -> tuple[str, str]:
		evidence = self._evidence("Payment Proof", "Cash Receipt")
		frappe.set_user(self.operator)
		created = create_contract_estimate(
			{
				"contract": contract,
				"period_start": "2026-02-01",
				"period_end": "2026-02-28",
				"cost_kind": "Labor",
				"lines": [
					{
						"contract_line": "LAB-001",
						"description": "Avance ejecutado",
						"cost_kind": "Labor",
						"quantity": 1,
						"amount": amount,
					}
				],
				"advance_amortization": advance,
				"retention_amount": retention,
				"fine_amount": fine,
				"deduction_amount": deduction,
				"evidence": evidence,
				"requester": self.operator,
				"idempotency_key": _key("contract-estimate"),
			}
		)
		estimate = str(created["estimate"])
		frappe.set_user(self.manager)
		transition_contract_estimate(estimate, "Pending Approval", _key("estimate-review"))
		transition_contract_estimate(estimate, "Approved", _key("estimate-approved"))
		return estimate, evidence

	def test_contract_lifecycle_finance_amendment_retention_and_canonical_resolution(self) -> None:
		contract, entity, _profile, source = self._contract(labor=1000, materials=500)
		amendment_evidence = self._evidence()
		frappe.set_user(self.manager)
		amendment = create_contract_amendment(
			{
				"contract": contract,
				"amendment_type": "Increase",
				"effective_date": "2026-03-01",
				"labor_delta": 200,
				"material_delta": 0,
				"new_end_date": "2027-02-28",
				"scope_change": "Alcance ampliado y versionado",
				"reason": "Ampliación autorizada",
				"evidence": amendment_evidence,
				"idempotency_key": _key("contract-amendment"),
			}
		)
		for status in ("In Review", "Approved", "Active"):
			transition_contract_amendment(str(amendment["amendment"]), status, _key(f"amendment-{status}"))
		doc = frappe.get_doc("NXR Contract", contract)
		self.assertEqual(Decimal("1000.00"), Decimal(str(doc.original_labor_amount)))
		self.assertEqual(Decimal("1200.00"), Decimal(str(doc.current_labor_amount)))
		self.assertEqual(2, doc.version)

		payment_evidence = self._evidence("Payment Proof", "Cash Receipt")
		frappe.set_user(self.executor)
		advance = disburse_contract_advance(
			{
				"contract": contract,
				"amount": 200,
				"allocations": [{"source": source, "amount_hnl": 200}],
				"operation_date": "2026-02-01",
				"due_date": "2026-12-31",
				"payment_method": "Cash",
				"evidence": payment_evidence,
				"requester": self.operator,
				"approved_by": self.manager,
				"idempotency_key": _key("contract-advance"),
			}
		)
		estimate, _evidence = self._estimate(contract, 500, advance=100, retention=50, fine=20, deduction=10)
		frappe.set_user(self.executor)
		paid = execute_contract_estimate_payment(
			{
				"estimate": estimate,
				"advance_operation": advance["operation"],
				"allocations": [{"source": source, "amount_hnl": 320}],
				"payment_method": "Cash",
				"external_reference": "PAY-001",
				"operation_date": "2026-03-05",
				"requester": self.operator,
				"approved_by": self.manager,
				"idempotency_key": _key("contract-pay"),
			}
		)
		self.assertTrue(paid["payment_operation"])
		self.assertTrue(paid["settlement_operation"])
		doc.reload()
		self.assertEqual(Decimal("500.00"), Decimal(str(doc.executed_labor_amount)))
		self.assertEqual(Decimal("500.00"), Decimal(str(doc.executed_amount)))
		self.assertEqual(Decimal("1200.00"), Decimal(str(doc.pending_amount)))
		self.assertEqual(Decimal("320.00"), Decimal(str(doc.paid_amount)))
		self.assertEqual(Decimal("100.00"), Decimal(str(doc.advance_balance)))
		self.assertEqual(Decimal("50.00"), Decimal(str(doc.retention_balance)))
		self.assertEqual(Decimal("20.00"), Decimal(str(doc.fine_amount)))
		self.assertEqual(Decimal("10.00"), Decimal(str(doc.deduction_amount)))

		frappe.set_user(self.executor)
		returned = return_contract_retention(
			{
				"contract": contract,
				"amount": 50,
				"allocations": [{"source": source, "amount_hnl": 50}],
				"payment_method": "Cash",
				"external_reference": "RET-001",
				"evidence": payment_evidence,
				"requester": self.operator,
				"approved_by": self.manager,
				"idempotency_key": _key("contract-retention-return"),
			}
		)
		self.assertEqual("0.00", returned["retention_balance"])
		with self.assertRaisesRegex(frappe.ValidationError, "excede"):
			return_contract_retention(
				{
					"contract": contract,
					"amount": 1,
					"allocations": [{"source": source, "amount_hnl": 1}],
					"payment_method": "Cash",
					"requester": self.operator,
					"approved_by": self.manager,
					"idempotency_key": _key("contract-retention-excess"),
				}
			)

		payment_tx = frappe.db.get_value(
			"NXR Contract Transaction", {"estimate": estimate, "transaction_type": "Payment"}, "name"
		)
		frappe.set_user(self.executor)
		correction_evidence = self._evidence("Payment Proof", "Cash Receipt")
		frappe.set_user(self.executor)
		corrected = correct_contract_transaction(
			{
				"transaction": payment_tx,
				"correction_operation": "REAL_RETURN",
				"amount": 20,
				"allocations": [{"source": source, "amount_hnl": 20}],
				"evidence": correction_evidence,
				"payment_method": "Cash",
				"external_reference": "CORR-001",
				"requester": self.operator,
				"approved_by": self.manager,
				"reason": "Devolución parcial comprobada",
				"idempotency_key": _key("contract-correction"),
			}
		)
		self.assertEqual("REAL_RETURN", corrected["correction_operation"])
		doc.reload()
		self.assertEqual(Decimal("350.00"), Decimal(str(doc.paid_amount)))

		target = self._entity("Contratista canónico")
		frappe.set_user(self.manager)
		consolidate_entities(
			entity, target, "Consolidación contractual no destructiva", _key("contract-consolidate")
		)
		detail = get_contract(contract)
		self.assertEqual(entity, detail["contractor"])
		self.assertEqual(target, detail["canonical_contractor"])
		self.assertTrue(frappe.db.exists("NXR Contract", {"name": contract, "contractor": entity}))
		self.assertTrue(
			frappe.db.exists(
				"NXR Audit Event", {"reference_doctype": "NXR Contract", "reference_name": contract}
			)
		)

		balance = next(row for row in list_source_balances(self.project) if row["source"] == source)
		self.assertEqual(Decimal("9450.00"), Decimal(str(balance["balance_hnl"])))

	def test_payment_rollback_and_terminal_liquidation(self) -> None:
		contract, _entity, _profile, source = self._contract(labor=200, materials=0)
		estimate, _evidence = self._estimate(contract, 200)
		frappe.set_user(self.executor)
		frappe.flags.nexora_fail_after_allocation = 1
		with self.assertRaisesRegex(frappe.ValidationError, "inyectado"):
			execute_contract_estimate_payment(
				{
					"estimate": estimate,
					"allocations": [{"source": source, "amount_hnl": 200}],
					"payment_method": "Cash",
					"requester": self.operator,
					"approved_by": self.manager,
					"idempotency_key": _key("contract-payment-rollback"),
				}
			)
		frappe.flags.nexora_fail_after_allocation = None
		self.assertEqual("Approved", frappe.db.get_value("NXR Contract Estimate", estimate, "status"))
		self.assertEqual(0, frappe.db.get_value("NXR Contract", contract, "executed_labor_amount"))
		frappe.set_user(self.executor)
		execute_contract_estimate_payment(
			{
				"estimate": estimate,
				"allocations": [{"source": source, "amount_hnl": 200}],
				"payment_method": "Cash",
				"requester": self.operator,
				"approved_by": self.manager,
				"idempotency_key": _key("contract-payment-success"),
			}
		)
		frappe.set_user(self.manager)
		for status in ("Completed", "In Liquidation", "Liquidated"):
			transition_contract(contract, status, _key(f"contract-liquidation-{status}"))
		self.assertEqual("Liquidated", frappe.db.get_value("NXR Contract", contract, "status"))
		self.assertTrue(
			frappe.db.exists(
				"NXR Contract Transaction", {"contract": contract, "transaction_type": "Liquidation"}
			)
		)
		doc = frappe.get_doc("NXR Contract", contract)
		doc.current_scope = "Cambio prohibido"
		with self.assertRaisesRegex(frappe.ValidationError, "terminal"):
			from nexora.financial.context import service_write

			with service_write():
				doc.save(ignore_permissions=True)

	def test_amendment_controls_and_profile_overlap(self) -> None:
		contract, entity, _profile, _source = self._contract(labor=300, materials=0)
		frappe.set_user(self.manager)
		with self.assertRaisesRegex(frappe.ValidationError, "adenda versionada"):
			transition_contract(contract, "Suspended", _key("direct-suspension"), "No permitido")
		with self.assertRaisesRegex(frappe.ValidationError, "superpuesto"):
			create_contractor_profile(
				{
					"entity": entity,
					"classification": "Company",
					"valid_from": "2027-01-01",
					"valid_until": "2028-01-01",
					"compliance_status": "Valid",
					"idempotency_key": _key("overlap-profile"),
				}
			)
		evidence = self._evidence()
		frappe.set_user(self.manager)
		with self.assertRaisesRegex(frappe.ValidationError, "incremento"):
			create_contract_amendment(
				{
					"contract": contract,
					"amendment_type": "Increase",
					"labor_delta": -1,
					"reason": "Inválida",
					"evidence": evidence,
					"idempotency_key": _key("invalid-amendment"),
				}
			)

	def test_server_permissions_and_overpayment_rejection(self) -> None:
		contract, _entity, _profile, _source = self._contract(labor=300, materials=0)
		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			create_contract_estimate(
				{
					"contract": contract,
					"cost_kind": "Labor",
					"lines": [],
					"idempotency_key": _key("contract-denied"),
				}
			)
		frappe.set_user(self.operator)
		evidence = self._evidence("Payment Proof", "Cash Receipt")
		with self.assertRaisesRegex(frappe.ValidationError, "excede"):
			create_contract_estimate(
				{
					"contract": contract,
					"period_start": "2026-01-01",
					"period_end": "2026-01-31",
					"cost_kind": "Labor",
					"lines": [
						{
							"contract_line": "LAB-001",
							"description": "Exceso",
							"cost_kind": "Labor",
							"quantity": 1,
							"amount": 301,
						}
					],
					"evidence": evidence,
					"idempotency_key": _key("contract-overestimate"),
				}
			)


if __name__ == "__main__":
	import unittest

	unittest.main()
