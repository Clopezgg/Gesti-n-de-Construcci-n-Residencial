from __future__ import annotations

import uuid
from decimal import Decimal

import frappe
from frappe.tests.utils import FrappeTestCase

test_dependencies = ["Project", "Cost Center"]

from nexora.budget.service import activate_budget, create_budget
from nexora.financial.commitments import create_commitment, execute_commitment, release_commitment
from nexora.financial.sources import create_fund_source


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


class TestBudgetCommitmentEnforcementMariaDB(FrappeTestCase):
	"""NXR-PRE-0008: el presupuesto debe bloquear un compromiso que lo exceda.

	Requiere bench + MariaDB reales (test_dependencies genera un centro de costo hoja).
	No se pudo ejecutar en el entorno de esta sesión (sin bench/Frappe/MariaDB); se
	documenta como NO DEMOSTRADO hasta que corra en `server-tests-mariadb.yml`.
	"""

	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		marker = uuid.uuid4().hex[:8]
		cls.project = str(
			frappe.get_doc(
				{"doctype": "Project", "project_name": f"_Test Budget Commitment {marker}", "status": "Open"}
			)
			.insert(ignore_permissions=True)
			.name
		)
		cls.manager = _ensure_user(
			f"nxr-budget-commit-manager-{marker}@example.test", "NEXORA Finance Manager"
		)
		cls.executor = _ensure_user(
			f"nxr-budget-commit-executor-{marker}@example.test", "NEXORA Finance Operator"
		)
		cls.requester = _ensure_user(
			f"nxr-budget-commit-requester-{marker}@example.test", "NEXORA Finance Operator"
		)
		cls.cost_center = frappe.db.get_value("Cost Center", {"is_group": 0}, "name")
		if not cls.cost_center:
			raise AssertionError("Cost Center test dependency did not create a leaf cost center")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _source(self, amount: int) -> str:
		frappe.set_user(self.manager)
		return create_fund_source(
			{
				"idempotency_key": _key("budget-commit-source"),
				"source_name": "Fuente para compromiso presupuestado",
				"channel": "Remittance",
				"project": self.project,
				"source_date": frappe.utils.today(),
				"currency": "HNL",
				"original_amount": amount,
				"exchange_rate": 1,
				"origin_or_sender": "Prueba NXR-PRE-0008",
				"custodian": self.manager,
			}
		)["fund_source"]

	def _budget_line(self, budget_name: str) -> object:
		lines = frappe.get_all(
			"NXR Budget Line",
			filters={"parent": budget_name, "parenttype": "NXR Budget", "cost_center": self.cost_center},
			fields=["name", "approved_hnl", "committed_hnl", "executed_hnl", "available_hnl"],
		)
		self.assertEqual(
			1, len(lines), "se esperaba exactamente una línea de presupuesto para el centro de costo"
		)
		return lines[0]

	def _budget_with_line(self, approved_hnl: int) -> str:
		frappe.set_user(self.manager)
		budget = create_budget(
			{
				"idempotency_key": _key("budget-commit"),
				"project": self.project,
				"title": "Presupuesto con enforcement",
				"effective_date": frappe.utils.today(),
				"lines": [
					{
						"economic_category": "CONSTRUCTION_MATERIALS",
						"cost_center": self.cost_center,
						"description": "Línea con enforcement",
						"approved_hnl": approved_hnl,
					}
				],
			}
		)["budget"]
		activate_budget({"budget": budget})
		return budget

	def test_commitment_exceeding_budget_is_rejected_and_nothing_is_created(self) -> None:
		budget = self._budget_with_line(1000)
		source = self._source(5000)
		frappe.set_user(self.manager)
		key = _key("commit-overspend")
		with self.assertRaisesRegex(frappe.ValidationError, "Compromiso no permitido"):
			create_commitment(
				{
					"idempotency_key": key,
					"project": self.project,
					"amount_hnl": 1500,
					"allocations": [{"source": source, "amount_hnl": 1500}],
					"cost_center": self.cost_center,
					"economic_category": "CONSTRUCTION_MATERIALS",
					"requester": self.requester,
					"approved_by": self.manager,
					"description": "Compromiso que excede el presupuesto",
				}
			)
		# No debe crearse el compromiso, ni la operación, ni la clave de idempotencia:
		# el rechazo ocurre antes de cualquier mutación (savepoint sin confirmar).
		self.assertFalse(frappe.db.exists("NXR Idempotency Record", key))
		self.assertFalse(frappe.db.exists("NXR Commitment", {"idempotency_key": key}))
		line = self._budget_line(budget)
		self.assertEqual(Decimal("0.00"), Decimal(str(line.committed_hnl)))
		self.assertEqual(Decimal("1000.00"), Decimal(str(line.available_hnl)))

	def test_commitment_within_budget_reserves_execute_and_release_lifecycle(self) -> None:
		budget = self._budget_with_line(1000)
		source = self._source(5000)
		frappe.set_user(self.manager)
		commitment = create_commitment(
			{
				"idempotency_key": _key("commit-ok"),
				"project": self.project,
				"amount_hnl": 400,
				"allocations": [{"source": source, "amount_hnl": 400}],
				"cost_center": self.cost_center,
				"economic_category": "CONSTRUCTION_MATERIALS",
				"requester": self.requester,
				"approved_by": self.manager,
				"description": "Compromiso dentro del presupuesto",
			}
		)
		line = self._budget_line(budget)
		self.assertEqual(Decimal("400.00"), Decimal(str(line.committed_hnl)))
		self.assertEqual(Decimal("600.00"), Decimal(str(line.available_hnl)))
		stored = frappe.get_doc("NXR Commitment", commitment["commitment"])
		self.assertEqual(budget, stored.budget)
		self.assertEqual(line.name, stored.budget_line)

		frappe.set_user(self.executor)
		execute_commitment(
			{
				"idempotency_key": _key("commit-ok-execute"),
				"commitment": commitment["commitment"],
				"amount_hnl": 150,
				"allocations": [{"source": source, "amount_hnl": 150}],
				"requester": self.requester,
				"approved_by": self.manager,
			}
		)
		line = self._budget_line(budget)
		self.assertEqual(Decimal("250.00"), Decimal(str(line.committed_hnl)))
		self.assertEqual(Decimal("150.00"), Decimal(str(line.executed_hnl)))
		self.assertEqual(Decimal("600.00"), Decimal(str(line.available_hnl)))

		frappe.set_user(self.manager)
		release_commitment(
			{
				"idempotency_key": _key("commit-ok-release"),
				"commitment": commitment["commitment"],
				"amount_hnl": 250,
				"allocations": [{"source": source, "amount_hnl": 250}],
				"requester": self.requester,
				"approved_by": self.manager,
			}
		)
		line = self._budget_line(budget)
		self.assertEqual(Decimal("0.00"), Decimal(str(line.committed_hnl)))
		self.assertEqual(Decimal("150.00"), Decimal(str(line.executed_hnl)))
		self.assertEqual(Decimal("850.00"), Decimal(str(line.available_hnl)))

	def test_commitment_without_cost_center_is_not_budget_constrained(self) -> None:
		# Alcance documentado: sin cost_center no hay línea de presupuesto que resolver,
		# así que esta regla no aplica (no es una excepción silenciosa a una regla que
		# sí aplicaría). Ver docs/nexora/NEXORA_GAP_ANALISIS_BLOQUE_12.md.
		self._budget_with_line(1000)
		source = self._source(50000)
		frappe.set_user(self.manager)
		commitment = create_commitment(
			{
				"idempotency_key": _key("commit-no-cc"),
				"project": self.project,
				"amount_hnl": 20000,
				"allocations": [{"source": source, "amount_hnl": 20000}],
				"requester": self.requester,
				"approved_by": self.manager,
				"description": "Compromiso sin centro de costo",
			}
		)
		stored = frappe.get_doc("NXR Commitment", commitment["commitment"])
		self.assertFalse(stored.budget)
		self.assertFalse(stored.budget_line)
