from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

test_dependencies = ["Project", "Cost Center"]

from nexora.budget.core import InvalidTransition
from nexora.budget.service import activate_budget, cancel_budget, close_budget, create_budget


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


class TestBudgetLifecycleMariaDB(FrappeTestCase):
	"""`close_budget`/`cancel_budget` solo tenían cobertura de contrato — nunca se
	habían ejercido contra Frappe/MariaDB real. A diferencia de `create_budget`/
	`activate_budget`/`amend_budget` (cubiertos por `test_budget_commitment_
	integration.py` y `test_budget_as_of_integration.py`), estas dos transiciones
	terminales del presupuesto nunca se habían comprobado: que respetan la máquina
	de estados real (`BUDGET_TRANSITIONS` en `budget/core.py` — `cancel_budget`
	solo es legal desde `Draft`, `close_budget` solo desde `Active`, y ambos
	destinos son terminales) y que están reservadas a roles gerenciales.
	"""

	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		marker = uuid.uuid4().hex[:8]
		cls.project = str(
			frappe.get_doc(
				{"doctype": "Project", "project_name": f"_Test Budget Lifecycle {marker}", "status": "Open"}
			)
			.insert(ignore_permissions=True)
			.name
		)
		cls.manager = _ensure_user(f"nxr-budget-life-manager-{marker}@example.test", "NEXORA Finance Manager")
		cls.viewer = _ensure_user(f"nxr-budget-life-viewer-{marker}@example.test", "NEXORA Project Viewer")
		cls.cost_center = frappe.db.get_value("Cost Center", {"is_group": 0}, "name")
		if not cls.cost_center:
			raise AssertionError("Cost Center test dependency did not create a leaf cost center")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _draft_budget(self) -> str:
		frappe.set_user(self.manager)
		return create_budget(
			{
				"idempotency_key": _key("budget-lifecycle"),
				"project": self.project,
				"title": "Presupuesto de ciclo de vida",
				"effective_date": frappe.utils.today(),
				"lines": [
					{
						"economic_category": "CONSTRUCTION_MATERIALS",
						"cost_center": self.cost_center,
						"description": "Línea de ciclo de vida",
						"approved_hnl": 1000,
					}
				],
			}
		)["budget"]

	def test_cancel_is_only_legal_from_draft_and_is_terminal(self) -> None:
		frappe.set_user(self.manager)
		budget = self._draft_budget()
		cancelled = cancel_budget({"budget": budget})
		self.assertEqual("Cancelled", cancelled["status"])
		self.assertEqual("Cancelled", frappe.get_doc("NXR Budget", budget).status)
		self.assertTrue(
			frappe.db.exists("NXR Audit Event", {"reference_doctype": "NXR Budget", "reference_name": budget})
		)

		# Terminal: un presupuesto cancelado no puede activarse ni volver a
		# cancelarse.
		with self.assertRaises(InvalidTransition):
			activate_budget({"budget": budget})
		with self.assertRaises(InvalidTransition):
			cancel_budget({"budget": budget})

	def test_cancel_is_rejected_once_the_budget_is_active(self) -> None:
		frappe.set_user(self.manager)
		budget = self._draft_budget()
		activate_budget({"budget": budget})
		# Un presupuesto activo ya está en uso: cancelarlo (en vez de cerrarlo)
		# borraría esa historia sin dejar rastro de ejecución. Solo un borrador
		# puede cancelarse; uno activo se cierra.
		with self.assertRaises(InvalidTransition):
			cancel_budget({"budget": budget})

	def test_close_is_only_legal_from_active_and_is_terminal(self) -> None:
		frappe.set_user(self.manager)
		budget = self._draft_budget()
		# Un borrador todavía no comprometió nada: cerrarlo no tiene sentido de
		# negocio, solo cancelarlo.
		with self.assertRaises(InvalidTransition):
			close_budget({"budget": budget})

		activate_budget({"budget": budget})
		closed = close_budget({"budget": budget})
		self.assertEqual("Closed", closed["status"])
		self.assertEqual("Closed", frappe.get_doc("NXR Budget", budget).status)

		# Terminal: un presupuesto cerrado no puede reabrirse ni cerrarse de nuevo.
		with self.assertRaises(InvalidTransition):
			close_budget({"budget": budget})
		with self.assertRaises(InvalidTransition):
			cancel_budget({"budget": budget})

	def test_a_viewer_cannot_close_or_cancel_a_budget(self) -> None:
		frappe.set_user(self.manager)
		draft_budget = self._draft_budget()
		active_budget = self._draft_budget()
		activate_budget({"budget": active_budget})

		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			cancel_budget({"budget": draft_budget})
		with self.assertRaises(frappe.PermissionError):
			close_budget({"budget": active_budget})


if __name__ == "__main__":
	import unittest

	unittest.main()
