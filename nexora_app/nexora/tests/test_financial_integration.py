from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.financial.analytics import list_central_operations, prepare_central_payload
from nexora.financial.commitments import create_commitment, execute_commitment, release_commitment
from nexora.financial.operations import execute_financial_operation, preview_financial_operation
from nexora.financial.sources import create_fund_source, list_source_balances


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


class TestNexoraFinancialMariaDB(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.project = _ensure_project("_Test Project")
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
		reclassification = {
			"idempotency_key": _key("reclass-zero"),
			"operation_type": "Reclassification",
			"project": self.project,
			"amount_hnl": 0,
			"allocations": [],
		}
		with self.assertRaisesRegex(frappe.ValidationError, "importe positivo"):
			execute_financial_operation(reclassification)
		reclassification["idempotency_key"] = _key("reclass")
		reclassification["amount_hnl"] = 100
		execute_financial_operation(reclassification)
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


class TestNexoraIncomeCancellationMariaDB(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.project = _ensure_project("_Test Income Cancellation")
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

	def test_manager_cancels_unused_income_from_standard_form(self):
		created = self._source(1250)
		frappe.set_user(self.manager)
		doc = frappe.get_doc("NXR Fund Source", created["fund_source"])
		doc.request_cancellation = 1
		doc.cancellation_reason = "Monto registrado por error durante la prueba."
		doc.save()

		self.assertEqual("Cancelled", doc.status)
		self.assertTrue(doc.cancellation_operation)
		self.assertEqual(self.manager, doc.cancelled_by)
		self.assertTrue(doc.cancelled_at)
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
		self.assertEqual(
			frappe.db.get_value("NXR Operation Effect", {"operation": created["operation"]}),
			effects[1].reverses_effect,
		)

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
		doc = frappe.get_doc("NXR Fund Source", created["fund_source"])
		doc.request_cancellation = 1
		doc.cancellation_reason = "Este ingreso ya fue utilizado y no debe anularse."
		with self.assertRaisesRegex(frappe.ValidationError, "movimientos relacionados"):
			doc.save()
		self.assertEqual("Active", frappe.db.get_value("NXR Fund Source", created["fund_source"], "status"))

	def test_operator_cannot_cancel_income(self):
		created = self._source(500)
		frappe.set_user(self.operator)
		doc = frappe.get_doc("NXR Fund Source", created["fund_source"])
		doc.request_cancellation = 1
		doc.cancellation_reason = "El operador no puede aprobar esta anulación."
		with self.assertRaises(frappe.PermissionError):
			doc.save()


class TestFinancialReadProjectScopingMariaDB(FrappeTestCase):
	"""NXR-SEC-0001 (Bloque 19): regresión real de la corrección de acceso por
	proyecto en `financial.sources.list_source_balances` y
	`financial.analytics.list_central_operations` — un "NEXORA Project Viewer"
	sin `User Permission` explícito no debe poder leer ninguno de los dos."""

	def setUp(self) -> None:
		frappe.set_user("Administrator")
		marker = uuid.uuid4().hex[:10]
		self.project = _ensure_project(f"_Test SEC-0001 Financial {marker}")
		self.cost_center = frappe.db.get_value("Cost Center", {"is_group": 0}, "name")
		if not self.cost_center:
			raise AssertionError("Cost Center test dependency did not create a leaf cost center")
		self.manager = _ensure_user(f"nxr-secfin-manager-{marker}@example.test", "NEXORA Finance Manager")
		self.viewer = _ensure_user(f"nxr-secfin-viewer-{marker}@example.test", "NEXORA Project Viewer")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def test_list_source_balances_rejects_a_viewer_without_an_explicit_project_grant(self) -> None:
		frappe.set_user(self.manager)
		create_fund_source(
			{
				"idempotency_key": _key("secfin-source"),
				"source_name": f"Fuente SEC-0001 {uuid.uuid4().hex[:8]}",
				"channel": "Remittance",
				"project": self.project,
				"currency": "HNL",
				"original_amount": 500,
				"exchange_rate": 1,
				"origin_or_sender": "Remitente CI",
				"custodian": self.manager,
			}
		)
		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			list_source_balances(self.project)

		frappe.set_user("Administrator")
		frappe.get_doc(
			{"doctype": "User Permission", "user": self.viewer, "allow": "Project", "for_value": self.project}
		).insert(ignore_permissions=True)
		frappe.set_user(self.viewer)
		balances = list_source_balances(self.project)
		self.assertEqual(1, len(balances))

	def test_list_central_operations_rejects_a_viewer_without_an_explicit_project_grant(self) -> None:
		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			list_central_operations(self.project)

		frappe.set_user("Administrator")
		frappe.get_doc(
			{"doctype": "User Permission", "user": self.viewer, "allow": "Project", "for_value": self.project}
		).insert(ignore_permissions=True)
		frappe.set_user(self.viewer)
		# Sin operaciones creadas, la lista real vacía sigue siendo la prueba de que
		# el chequeo de acceso ya pasó (de lo contrario habría lanzado antes de
		# llegar a `frappe.get_all`).
		self.assertEqual([], list_central_operations(self.project))

	def test_preview_financial_operation_rejects_a_viewer_without_an_explicit_project_grant(self) -> None:
		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			preview_financial_operation({"project": self.project, "operation_type": "Outflow"})

		frappe.set_user("Administrator")
		frappe.get_doc(
			{"doctype": "User Permission", "user": self.viewer, "allow": "Project", "for_value": self.project}
		).insert(ignore_permissions=True)
		frappe.set_user(self.viewer)
		# El resto del payload es intencionalmente incompleto: la prueba real que
		# importa aquí es que el rechazo, si lo hay, ya no es `PermissionError` —
		# la validación de negocio posterior no es el hallazgo de NXR-SEC-0001.
		try:
			preview_financial_operation({"project": self.project, "operation_type": "Outflow"})
		except frappe.PermissionError:
			self.fail("Un viewer con permiso explícito no debería recibir PermissionError.")
		except frappe.ValidationError:
			pass

	def test_prepare_central_payload_rejects_a_viewer_without_an_explicit_project_grant(self) -> None:
		frappe.set_user(self.manager)
		source = create_fund_source(
			{
				"idempotency_key": _key("secfin-central-source"),
				"source_name": f"Fuente central SEC-0001 {uuid.uuid4().hex[:8]}",
				"channel": "Remittance",
				"project": self.project,
				"currency": "HNL",
				"original_amount": 1000,
				"exchange_rate": 1,
				"origin_or_sender": "Remitente CI",
				"custodian": self.manager,
			}
		)["fund_source"]
		payload = {
			"idempotency_key": _key("secfin-central-prepare"),
			"operation_code": "CONSTRUCTION_PAYMENT",
			"economic_category": "CONSTRUCTION_MATERIALS",
			"project": self.project,
			"amount_hnl": 100,
			"allocations": [{"source": source, "amount_hnl": 100}],
			"cost_center": self.cost_center,
			"beneficiary_doctype": "User",
			"beneficiary": self.manager,
			"requester": self.manager,
			"approved_by": self.manager,
		}
		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			prepare_central_payload(payload)


if __name__ == "__main__":
	import unittest

	unittest.main()
