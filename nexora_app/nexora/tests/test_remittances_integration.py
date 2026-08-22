from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.financial.central_treasury import CENTRAL_REMITTANCE_KEY
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

	def _payload(self, destinations=None, key=None, **overrides):
		frappe.set_user(self.executor)
		rows = list(destinations or [{"label": "Legacy", "amount_hnl": 100000}])
		return {
			"idempotency_key": key or _key("remittance"),
			"channel": "Remittance",
			"currency": "HNL",
			"original_amount": sum(row["amount_hnl"] for row in rows),
			"exchange_rate": 1,
			"origin_or_sender": "Remitente CI",
			"custodian": self.executor,
			**overrides,
		}

	def test_one_remittance_creates_one_central_fund_source(self) -> None:
		frappe.set_user(self.executor)
		result = create_remittance(self._payload([{"label": "Central", "amount_hnl": 100000}]))
		self.assertRegex(result["remittance"], r"^\d{12}$")
		self.assertEqual(1, len(result["destinations"]))
		self.assertEqual("Cuenta Central de Remesas", result["destinations"][0]["label"])
		doc = frappe.get_doc("NXR Remittance", result["remittance"])
		self.assertEqual(result["financial_account"], doc.financial_account)
		self.assertEqual(
			CENTRAL_REMITTANCE_KEY,
			frappe.db.get_value("NXR Financial Account", doc.financial_account, "technical_key"),
		)
		self.assertEqual(1, len(doc.destinations))
		source = doc.destinations[0].fund_source
		self.assertEqual(source, result["fund_source"])
		self.assertEqual(None, frappe.db.get_value("NXR Fund Source", source, "project"))
		central = {row["source"]: row for row in list_source_balances() if row["source"] == source}
		self.assertEqual("100000.00", central[source]["balance_hnl"])

	def test_two_remittances_share_one_account_but_keep_two_sources(self) -> None:
		frappe.set_user(self.executor)
		first = create_remittance(self._payload([{"label": "Primera", "amount_hnl": 100}]))
		second = create_remittance(self._payload([{"label": "Segunda", "amount_hnl": 200}]))
		self.assertEqual(first["financial_account"], second["financial_account"])
		self.assertNotEqual(first["fund_source"], second["fund_source"])
		self.assertEqual(1, frappe.db.count("NXR Fund Source", {"remittance": first["remittance"]}))
		self.assertEqual(1, frappe.db.count("NXR Fund Source", {"remittance": second["remittance"]}))

	def test_alternate_account_project_and_legacy_destinations_are_rejected(self) -> None:
		frappe.set_user(self.executor)
		invalid = (
			{"financial_account": "OTHER"},
			{"project": self.project},
			{"destinations": [{"label": "Legacy", "amount_hnl": 100}]},
		)
		for override in invalid:
			with self.subTest(override=override), self.assertRaises(frappe.ValidationError):
				create_remittance(self._payload([{"label": "Central", "amount_hnl": 100}], **override))

	def test_exchange_rate_is_not_rounded_before_conversion(self) -> None:
		frappe.set_user(self.executor)
		result = create_remittance(
			self._payload(
				[{"label": "Precisión", "amount_hnl": 100}],
				currency="USD",
				original_amount="100.00",
				exchange_rate="24.123456789",
			)
		)
		self.assertEqual("2412.35", result["total_amount_hnl"])

	def test_non_positive_remittance_amount_is_rejected(self) -> None:
		frappe.set_user(self.executor)
		before = frappe.db.count("NXR Fund Source")
		with self.assertRaisesRegex(frappe.ValidationError, "mayores que cero"):
			create_remittance(self._payload([{"label": "x", "amount_hnl": 0}]))
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
		self.assertEqual(1, len(cancellation["sources"]))
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
