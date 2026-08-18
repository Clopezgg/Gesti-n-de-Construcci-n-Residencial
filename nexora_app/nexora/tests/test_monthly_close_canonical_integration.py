from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.close.core import ReconciliationError
from nexora.close.monthly_canonical import (
	correct_monthly_close,
	create_monthly_close,
	list_monthly_closes,
	transition_monthly_close,
)
from nexora.close.service import reconcile_month


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


class TestMonthlyCloseCanonicalMariaDB(FrappeTestCase):
	"""`close.monthly_canonical` (create/transition/correct/list_monthly_close) solo
	tenía cobertura de contrato (`test_monthly_close_contract.py`: una clase simple
	sin `FrappeTestCase`, sin base de datos real) — a diferencia de su hermano
	`close.canonical_weekly`, que sí tiene `test_weekly_close_canonical_integration.
	py`. Nunca se había ejercido contra Frappe/MariaDB real el ciclo de vida
	completo (Draft → In Review → Approved, terminal, corrección) pese a ser un
	cierre financiero que bloquea el período — exactamente la clase de operación
	que este proyecto trata como de mayor riesgo si se ejecuta sin comprobar."""

	def setUp(self) -> None:
		super().setUp()
		frappe.set_user("Administrator")
		marker = uuid.uuid4().hex[:10]
		self.project = str(
			frappe.get_doc(
				{
					"doctype": "Project",
					"project_name": f"_Test NEXORA Monthly Close {marker}",
					"status": "Open",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		self.manager = _user(f"nxr-monthly-manager-{marker}@example.test", "NEXORA Finance Manager")
		self.viewer = _user(f"nxr-monthly-viewer-{marker}@example.test", "NEXORA Project Viewer")
		self.close_month = frappe.utils.getdate(frappe.utils.today()).strftime("%Y-%m")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def test_lifecycle_is_idempotent_locks_on_approval_and_rejects_duplicates(self) -> None:
		frappe.set_user(self.manager)
		payload = {
			"project": self.project,
			"close_month": self.close_month,
			"comments": "Cierre mensual de aceptación",
			"idempotency_key": _key("monthly-create"),
		}
		created = create_monthly_close(payload)
		self.assertEqual(created, create_monthly_close(payload))
		self.assertRegex(created["document_number"], r"^\d{12}$")
		self.assertEqual("nexora-analytics-v3-monthly", created["engine_version"])
		doc = frappe.get_doc("NXR Monthly Close", created["monthly_close"])
		self.assertEqual("Draft", doc.status)
		self.assertEqual(created["snapshot_hash"], doc.snapshot_hash)

		# Mientras el cierre siga en Draft, un segundo cierre con otra clave no
		# es un duplicado bloqueado: el guardián solo mira Closed/Approved. Eso
		# es lo que se comprueba después de aprobar, más abajo.

		reviewed = transition_monthly_close(
			{"monthly_close": created["monthly_close"], "status": "In Review"}
		)
		self.assertEqual("In Review", reviewed["status"])

		approved = transition_monthly_close({"monthly_close": created["monthly_close"], "status": "Approved"})
		self.assertEqual("Approved", approved["status"])
		doc.reload()
		self.assertEqual("Approved", doc.status)
		self.assertEqual(self.manager, doc.closed_by)
		self.assertIsNotNone(doc.closed_at)

		# Terminal: ni un segundo intento de aprobar ni una cancelación pueden
		# modificar un cierre ya aprobado directamente.
		with self.assertRaisesRegex(frappe.ValidationError, "terminal no puede modificarse"):
			transition_monthly_close({"monthly_close": created["monthly_close"], "status": "Cancelled"})

		# Ahora que está Approved, un segundo cierre no-correctivo del mismo
		# período también debe rechazarse (antes lo bloqueaba el Draft, ahora
		# lo bloquea el estado terminal Approved).
		with self.assertRaisesRegex(frappe.ValidationError, "Ya existe un cierre mensual"):
			create_monthly_close({**payload, "idempotency_key": _key("monthly-duplicate-after-approval")})

	def test_correction_requires_an_approved_original_and_links_to_it(self) -> None:
		frappe.set_user(self.manager)
		created = create_monthly_close(
			{
				"project": self.project,
				"close_month": self.close_month,
				"idempotency_key": _key("monthly-for-correction"),
			}
		)

		# Un cierre en Draft (no Approved) no puede corregirse mediante documento
		# enlazado: la corrección existe para preservar historia sobre algo ya
		# cerrado, no para editar un borrador.
		with self.assertRaisesRegex(frappe.ValidationError, "cierre mensual aprobado puede corregirse"):
			correct_monthly_close(
				{
					"monthly_close": created["monthly_close"],
					"correction_reason": "Motivo con más de diez caracteres",
					"idempotency_key": _key("monthly-correct-too-early"),
				}
			)

		transition_monthly_close({"monthly_close": created["monthly_close"], "status": "In Review"})
		transition_monthly_close({"monthly_close": created["monthly_close"], "status": "Approved"})

		with self.assertRaisesRegex(frappe.ValidationError, "explique la corrección"):
			correct_monthly_close(
				{
					"monthly_close": created["monthly_close"],
					"correction_reason": "corto",
					"idempotency_key": _key("monthly-correct-short-reason"),
				}
			)

		correction = correct_monthly_close(
			{
				"monthly_close": created["monthly_close"],
				"correction_reason": "Conciliación posterior documentada con evidencia",
				"idempotency_key": _key("monthly-correction"),
			}
		)
		self.assertNotEqual(created["monthly_close"], correction["monthly_close"])
		self.assertEqual(created["monthly_close"], correction["correction_of"])
		self.assertEqual("Approved", correction["status"])
		correction_doc = frappe.get_doc("NXR Monthly Close", correction["monthly_close"])
		self.assertEqual(created["monthly_close"], correction_doc.correction_of)
		self.assertEqual(self.project, correction_doc.project)
		self.assertEqual(self.close_month, correction_doc.close_month)

		# El original queda intacto: la corrección es un documento nuevo enlazado,
		# nunca una sobrescritura silenciosa del cierre aprobado.
		original = frappe.get_doc("NXR Monthly Close", created["monthly_close"])
		self.assertEqual("Approved", original.status)
		self.assertFalse(original.correction_of)

		listed = list_monthly_closes({"project": self.project})
		names = {row.name for row in listed["rows"]}
		self.assertIn(created["monthly_close"], names)
		self.assertIn(correction["monthly_close"], names)

	def test_a_viewer_can_list_but_cannot_create_transition_or_correct(self) -> None:
		frappe.set_user(self.manager)
		created = create_monthly_close(
			{
				"project": self.project,
				"close_month": self.close_month,
				"idempotency_key": _key("monthly-for-viewer"),
			}
		)

		frappe.set_user(self.viewer)
		# Sin permiso explícito de proyecto, "NEXORA Project Viewer" no está en
		# ALL_PROJECT_ROLES y no puede listar ni siquiera con permiso de lectura
		# genérico — mismo patrón ya usado en test_evidence_integration.py.
		with self.assertRaises(frappe.PermissionError):
			list_monthly_closes({"project": self.project})

		frappe.set_user("Administrator")
		grant = frappe.get_doc(
			{"doctype": "User Permission", "user": self.viewer, "allow": "Project", "for_value": self.project}
		).insert(ignore_permissions=True)
		try:
			frappe.set_user(self.viewer)
			listed = list_monthly_closes({"project": self.project})
			self.assertIn(created["monthly_close"], {row.name for row in listed["rows"]})
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("User Permission", grant.name, ignore_permissions=True)

		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			create_monthly_close(
				{
					"project": self.project,
					"close_month": self.close_month,
					"idempotency_key": _key("monthly-viewer-create-denied"),
				}
			)
		with self.assertRaises(frappe.PermissionError):
			transition_monthly_close({"monthly_close": created["monthly_close"], "status": "In Review"})
		with self.assertRaises(frappe.PermissionError):
			correct_monthly_close(
				{
					"monthly_close": created["monthly_close"],
					"correction_reason": "Motivo con más de diez caracteres",
					"idempotency_key": _key("monthly-viewer-correct-denied"),
				}
			)


class TestCloseReconciliationMariaDB(FrappeTestCase):
	"""GP-10: "conciliación descuadrada" — `close.service.reconcile_month`
	(no redirigido por `override_whitelisted_methods` en `hooks.py`, a
	diferencia de `create_monthly_close`/`transition_monthly_close`/
	`correct_monthly_close`/`list_monthly_closes`: sigue siendo el
	endpoint real y vivo, sin interfaz de navegador desde el Bloque 50)
	nunca se había ejercido contra Frappe/MariaDB real. Solo tenía
	cobertura pura sobre `close.core.reconcile()` en
	`test_close_core.py`, nunca a través del propio endpoint
	`@frappe.whitelist` (permisos server-side incluidos)."""

	def setUp(self) -> None:
		super().setUp()
		frappe.set_user("Administrator")
		marker = uuid.uuid4().hex[:10]
		self.manager = _user(f"nxr-reconcile-manager-{marker}@example.test", "NEXORA Finance Manager")
		self.viewer = _user(f"nxr-reconcile-viewer-{marker}@example.test", "NEXORA Project Viewer")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def test_viewer_is_rejected_matching_snapshots_reconcile_and_mismatches_are_rejected(
		self,
	) -> None:
		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			reconcile_month({"before": {"total": "100"}, "after": {"total": "100"}})

		frappe.set_user(self.manager)
		result = reconcile_month({"before": {"total": "100"}, "after": {"total": "100"}})
		self.assertTrue(result["reconciled"])

		with self.assertRaises(ReconciliationError):
			reconcile_month({"before": {"total": "100"}, "after": {"total": "150"}})


if __name__ == "__main__":
	import unittest

	unittest.main()
