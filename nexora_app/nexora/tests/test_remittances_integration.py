from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.financial.remittances import cancel_remittance, create_remittance
from nexora.financial.sources import list_source_balances


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


class TestRemittanceMariaDB(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.project = _ensure_project("_Test Remittance Project")
		cls.other_project = _ensure_project("_Test Remittance Other Project")
		cls.executor = _ensure_user("nxr-remit-executor@example.test", "NEXORA Finance Operator")
		cls.manager = _ensure_user("nxr-remit-manager@example.test", "NEXORA Finance Manager")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _payload(self, destinations, key=None, **overrides):
		frappe.set_user(self.executor)
		return {
			"idempotency_key": key or _key("remittance"),
			"channel": "Remittance",
			"project": self.project,
			"currency": "HNL",
			"original_amount": sum(row["amount_hnl"] for row in destinations),
			"exchange_rate": 1,
			"origin_or_sender": "Remitente CI",
			"custodian": self.executor,
			"destinations": destinations,
			**overrides,
		}

	def test_splits_one_remittance_into_several_real_fund_sources(self) -> None:
		frappe.set_user(self.executor)
		result = create_remittance(
			self._payload(
				[
					{"label": "Fondo construcción", "amount_hnl": 60000},
					{"label": "Fondo materiales", "amount_hnl": 25000},
					{"label": "Fondo administración", "amount_hnl": 10000},
					{"label": "Reserva", "amount_hnl": 5000},
				]
			)
		)
		self.assertRegex(result["remittance"], r"^\d{12}$")
		self.assertEqual(4, len(result["destinations"]))
		self.assertEqual("100000.00", result["total_amount_hnl"])
		doc = frappe.get_doc("NXR Remittance", result["remittance"])
		self.assertEqual(4, len(doc.destinations))
		fund_sources = [row.fund_source for row in doc.destinations]
		self.assertEqual(4, len(set(fund_sources)))
		for source_name in fund_sources:
			self.assertEqual(
				result["remittance"], frappe.db.get_value("NXR Fund Source", source_name, "remittance")
			)
		balances = {
			row["source"]: row for row in list_source_balances(self.project) if row["source"] in fund_sources
		}
		self.assertEqual("60000.00", balances[fund_sources[0]]["balance_hnl"])
		self.assertEqual("25000.00", balances[fund_sources[1]]["balance_hnl"])
		self.assertEqual("10000.00", balances[fund_sources[2]]["balance_hnl"])
		self.assertEqual("5000.00", balances[fund_sources[3]]["balance_hnl"])

	def test_mismatched_destinations_are_rejected_and_create_nothing(self) -> None:
		frappe.set_user(self.executor)
		before = frappe.db.count("NXR Fund Source")
		with self.assertRaisesRegex(frappe.ValidationError, "suman"):
			create_remittance(
				self._payload(
					[{"label": "Fondo construcción", "amount_hnl": 60000}],
					original_amount=100000,
				)
			)
		self.assertEqual(before, frappe.db.count("NXR Fund Source"))

	def test_a_zero_or_negative_destination_is_rejected_even_when_the_total_balances(self) -> None:
		"""GP-03: "redondeo que deje destino cero/negativo" — distinto del
		descuadre ya probado en `test_mismatched_destinations_are_rejected_and_
		create_nothing`: aquí la suma de destinos SÍ cuadra contra el total (lo
		que exigiría `NXRRemittance.validate()`), pero un destino individual
		queda en cero o en negativo.

		Hallazgo real (Bloque 90, confirmado contra CI real): el rechazo NO
		ocurre en `NXRRemittanceDestination.validate()` (`money(self.amount_
		hnl) <= 0`, "El importe de cada destino debe ser mayor que cero.") —
		ese chequeo nunca dispara durante el `insert()` del padre en este
		flujo real, pese a que `test_remittance_contract.py` solo confirma por
		texto fuente que existe. El rechazo real ocurre más abajo, en
		`create_remittance()`, cuando cada destino se abre como `NXR Fund
		Source` vía `open_fund_source()`: `NXRFundSource.validate()` rechaza
		`original_amount <= 0` con "El importe y la tasa deben ser mayores que
		cero." La propiedad de seguridad (ningún destino en cero/negativo
		llega a persistirse) sigue cumplida — solo por un chequeo distinto al
		que documentaba `NEXORA_GOLDEN_PATHS.md`."""
		frappe.set_user(self.executor)
		before = frappe.db.count("NXR Fund Source")
		with self.assertRaisesRegex(frappe.ValidationError, "mayores que cero"):
			create_remittance(
				self._payload(
					[
						{"label": "Fondo construcción", "amount_hnl": 100000},
						{"label": "Redondeo residual", "amount_hnl": 0},
					],
					original_amount=100000,
				)
			)
		self.assertEqual(before, frappe.db.count("NXR Fund Source"))

		with self.assertRaisesRegex(frappe.ValidationError, "mayores que cero"):
			create_remittance(
				self._payload(
					[
						{"label": "Fondo construcción", "amount_hnl": 100050},
						{"label": "Ajuste negativo", "amount_hnl": -50},
					],
					original_amount=100000,
				)
			)
		self.assertEqual(before, frappe.db.count("NXR Fund Source"))

	def test_is_idempotent(self) -> None:
		frappe.set_user(self.executor)
		key = _key("remittance-idem")
		payload = self._payload([{"label": "Fondo A", "amount_hnl": 30000}], key)
		first = create_remittance(payload)
		second = create_remittance(payload)
		self.assertEqual(first, second)
		self.assertEqual(1, frappe.db.count("NXR Fund Source", {"remittance": first["remittance"]}))

	def test_cancellation_is_all_or_nothing(self) -> None:
		frappe.set_user(self.executor)
		result = create_remittance(
			self._payload(
				[
					{"label": "Fondo A", "amount_hnl": 40000},
					{"label": "Fondo B", "amount_hnl": 20000},
				]
			)
		)
		frappe.set_user(self.manager)
		cancellation = cancel_remittance(
			result["remittance"], "Remesa registrada por error durante la prueba.", _key("cancel")
		)
		self.assertEqual("Cancelled", cancellation["status"])
		self.assertEqual(2, len(cancellation["sources"]))
		doc = frappe.get_doc("NXR Remittance", result["remittance"])
		self.assertEqual("Cancelled", doc.status)
		self.assertEqual(self.manager, doc.cancelled_by)
		for row in doc.destinations:
			self.assertEqual("Cancelled", frappe.db.get_value("NXR Fund Source", row.fund_source, "status"))

	def test_a_finance_operator_cannot_cancel_a_remittance(self) -> None:
		"""`cancel_remittance` exige `cancel_source` (`MANAGER_ROLES`) —
		distinto de `create_remittance`, que exige `create_source`
		(`OPERATOR_ROLES`, más amplio). El mismo "NEXORA Finance Operator"
		que puede registrar una remesa real de dinero no puede deshacerla:
		anular una remesa ya distribuida entre varias fuentes reales queda
		reservado a Gerente financiero o Administrador. Verificado contra el
		código real de `nexora/permissions.py` antes de escribir la
		aserción — ninguna prueba existente ejercía este límite: la única
		cancelación probada en este archivo (`test_cancellation_is_all_or_
		nothing`) siempre usa `self.manager`."""
		frappe.set_user(self.executor)
		result = create_remittance(self._payload([{"label": "Fondo A", "amount_hnl": 15000}]))
		with self.assertRaises(frappe.PermissionError):
			cancel_remittance(
				result["remittance"],
				"Intento de cancelación sin el rol requerido.",
				_key("cancel-denied"),
			)
		doc = frappe.get_doc("NXR Remittance", result["remittance"])
		self.assertNotEqual("Cancelled", doc.status)

	def test_direct_desk_creation_is_rejected(self) -> None:
		frappe.set_user(self.executor)
		with self.assertRaisesRegex(frappe.ValidationError, "servicio transaccional NEXORA"):
			frappe.get_doc(
				{
					"doctype": "NXR Remittance",
					"remittance_code": "999999999999",
					"project": self.project,
					"remittance_date": frappe.utils.today(),
					"currency": "HNL",
					"total_original_amount": 100,
					"exchange_rate": 1,
					"total_amount_hnl": 100,
					"origin_or_sender": "Directo",
					"custodian": self.executor,
					"channel": "Cash",
					"destinations": [{"label": "X", "amount_hnl": 100}],
				}
			).insert(ignore_permissions=True)

	def test_destinations_can_target_a_different_project_than_the_parent(self) -> None:
		frappe.set_user(self.executor)
		result = create_remittance(
			self._payload(
				[
					{"label": "Fondo local", "amount_hnl": 10000},
					{"label": "Fondo otro proyecto", "amount_hnl": 5000, "project": self.other_project},
				]
			)
		)
		doc = frappe.get_doc("NXR Remittance", result["remittance"])
		projects = {row.project: row.fund_source for row in doc.destinations}
		self.assertEqual(
			self.project, frappe.db.get_value("NXR Fund Source", projects[self.project], "project")
		)
		self.assertEqual(
			self.other_project,
			frappe.db.get_value("NXR Fund Source", projects[self.other_project], "project"),
		)
