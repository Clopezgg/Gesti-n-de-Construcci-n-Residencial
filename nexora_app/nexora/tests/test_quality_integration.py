"""NXR-CAL-0001: control de calidad real contra Frappe/MariaDB (Bloque 26).

Requiere bench + MariaDB reales. Cobertura pensada para la matriz mínima
honesta de este requisito: creación real ligada a un proyecto (y,
opcionalmente, a un `NXR Progress Record`), transición completa
Open→Failed→Corrected→Passed→Closed, transición inválida rechazada por la
máquina de estados real, lectura real por proyecto vía `list_quality_checks`
y su rechazo a un usuario sin acceso al proyecto — regresión directa de
NXR-SEC-0001.
"""

from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.progress.service import create_progress_record
from nexora.quality.core import InvalidTransition
from nexora.quality.service import create_quality_check, list_quality_checks, transition_quality_check


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
	return email


class TestQualityIntegrationMariaDB(FrappeTestCase):
	def setUp(self) -> None:
		frappe.set_user("Administrator")
		marker = uuid.uuid4().hex[:10]
		self.project = str(
			frappe.get_doc(
				{"doctype": "Project", "project_name": f"_Test NEXORA Calidad {marker}", "status": "Open"}
			)
			.insert(ignore_permissions=True)
			.name
		)
		self.manager = _ensure_user(f"nxr-quality-manager-{marker}@example.test", "NEXORA Finance Manager")
		self.viewer = _ensure_user(f"nxr-quality-viewer-{marker}@example.test", "NEXORA Project Viewer")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _create(self, **overrides) -> dict:
		payload = {
			"project": self.project,
			"phase": "Cimentación",
			"description": "Verificación de resistencia del concreto en zapatas.",
			"checked_by": self.manager,
			"check_date": frappe.utils.today(),
			"idempotency_key": _key("quality"),
		}
		payload.update(overrides)
		frappe.set_user(self.manager)
		return create_quality_check(payload)

	def test_create_records_a_real_document_linked_to_its_project(self) -> None:
		result = self._create()
		doc = frappe.get_doc("NXR Quality Check", result["name"])
		self.assertEqual("Open", doc.status)
		self.assertEqual(self.project, doc.project)
		self.assertEqual(self.manager, doc.checked_by)

	def test_create_can_link_a_real_progress_record(self) -> None:
		frappe.set_user(self.manager)
		progress = create_progress_record(
			{
				"project": self.project,
				"phase": "Cimentación",
				"description": "Vaciado de zapatas frente norte.",
				"progress_percent": 40,
				"recorded_date": frappe.utils.today(),
				"responsible": self.manager,
				"idempotency_key": _key("quality-progress"),
			}
		)
		result = self._create(progress_record=progress["name"])
		doc = frappe.get_doc("NXR Quality Check", result["name"])
		self.assertEqual(progress["name"], doc.progress_record)

	def test_full_lifecycle_from_open_to_closed_through_a_failed_correction(self) -> None:
		result = self._create()
		frappe.set_user(self.manager)
		failed = transition_quality_check(
			{"record": result["name"], "target_status": "Failed", "result": "Fail"}
		)
		self.assertEqual("Failed", failed["status"])
		corrected = transition_quality_check(
			{
				"record": result["name"],
				"target_status": "Corrected",
				"corrective_actions": "Se retiró y vació de nuevo el tramo afectado.",
			}
		)
		self.assertEqual("Corrected", corrected["status"])
		passed = transition_quality_check(
			{"record": result["name"], "target_status": "Passed", "result": "Pass"}
		)
		self.assertEqual("Passed", passed["status"])
		closed = transition_quality_check({"record": result["name"], "target_status": "Closed"})
		self.assertEqual("Closed", closed["status"])
		doc = frappe.get_doc("NXR Quality Check", result["name"])
		self.assertEqual("Pass", doc.result)
		self.assertIn("vació de nuevo", doc.corrective_actions)

	def test_invalid_transition_is_rejected_by_the_real_state_machine(self) -> None:
		result = self._create()
		frappe.set_user(self.manager)
		with self.assertRaises(InvalidTransition):
			transition_quality_check({"record": result["name"], "target_status": "Closed"})

	def test_list_quality_checks_returns_only_the_authorized_project(self) -> None:
		self._create()
		frappe.set_user(self.manager)
		rows = list_quality_checks({"project": self.project})
		self.assertEqual(1, len(rows))
		self.assertEqual(self.project, rows[0]["project"])

	def test_list_quality_checks_rejects_a_viewer_without_an_explicit_project_grant(self) -> None:
		"""Regresión directa de NXR-SEC-0001 (Bloque 19), aplicada al endpoint
		nuevo de este bloque."""
		self._create()
		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			list_quality_checks({"project": self.project})

		frappe.set_user("Administrator")
		frappe.get_doc(
			{"doctype": "User Permission", "user": self.viewer, "allow": "Project", "for_value": self.project}
		).insert(ignore_permissions=True)
		frappe.set_user(self.viewer)
		rows = list_quality_checks({"project": self.project})
		self.assertEqual(1, len(rows))


if __name__ == "__main__":
	import unittest

	unittest.main()
