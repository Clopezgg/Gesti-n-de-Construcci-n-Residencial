"""NXR-AVA-0006: avance real contra Frappe/MariaDB (Bloque 25).

Requiere bench + MariaDB reales; no se pudo ejecutar en el entorno de esta
sesión (sin bench/Frappe/MariaDB — confirmado por
``ModuleNotFoundError: No module named 'frappe'`` al intentar importarlo
aquí). Cobertura pensada para la matriz mínima honesta de este bloque:
creación real con foto adjunta, transición completa
Draft→Submitted→Approved, transición inválida rechazada por la máquina de
estados real (no solo por su copia pura ya probada en
``test_progress_core.py``), lectura real por proyecto vía
``list_progress_records`` (nuevo en este bloque) y su rechazo a un usuario sin
acceso al proyecto — regresión directa de NXR-SEC-0001.
"""

from __future__ import annotations

import json
import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.progress.core import InvalidTransition
from nexora.progress.service import (
	create_progress_record,
	list_progress_records,
	transition_progress_record,
)


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


class TestProgressIntegrationMariaDB(FrappeTestCase):
	def setUp(self) -> None:
		frappe.set_user("Administrator")
		marker = uuid.uuid4().hex[:10]
		self.project = str(
			frappe.get_doc(
				{"doctype": "Project", "project_name": f"_Test NEXORA Avance {marker}", "status": "Open"}
			)
			.insert(ignore_permissions=True)
			.name
		)
		self.manager = _ensure_user(f"nxr-progress-manager-{marker}@example.test", "NEXORA Finance Manager")
		self.viewer = _ensure_user(f"nxr-progress-viewer-{marker}@example.test", "NEXORA Project Viewer")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _create(self, **overrides) -> dict:
		payload = {
			"project": self.project,
			"phase": "Cimentación",
			"description": "Vaciado de zapatas completado en el frente norte.",
			"progress_percent": 35,
			"recorded_date": frappe.utils.today(),
			"responsible": self.manager,
			"photos": json.dumps(["/private/files/avance-demo.jpg"]),
			"idempotency_key": _key("progress"),
		}
		payload.update(overrides)
		frappe.set_user(self.manager)
		return create_progress_record(payload)

	def test_create_records_a_real_document_with_a_photo(self) -> None:
		result = self._create()
		doc = frappe.get_doc("NXR Progress Record", result["name"])
		self.assertEqual("Draft", doc.status)
		self.assertEqual(self.project, doc.project)
		self.assertIn("avance-demo.jpg", doc.photos)

	def test_full_transition_from_draft_to_approved(self) -> None:
		result = self._create()
		frappe.set_user(self.manager)
		submitted = transition_progress_record({"record": result["name"], "target_status": "Submitted"})
		self.assertEqual("Submitted", submitted["status"])
		approved = transition_progress_record({"record": result["name"], "target_status": "Approved"})
		self.assertEqual("Approved", approved["status"])

	def test_invalid_transition_is_rejected_by_the_real_state_machine(self) -> None:
		"""Regresión: la máquina de estados real (no solo su copia pura) debe
		rechazar un salto directo de Draft a Approved."""
		result = self._create()
		frappe.set_user(self.manager)
		with self.assertRaises(InvalidTransition):
			transition_progress_record({"record": result["name"], "target_status": "Approved"})

	def test_list_progress_records_returns_only_the_authorized_project(self) -> None:
		self._create()
		frappe.set_user(self.manager)
		rows = list_progress_records({"project": self.project})
		self.assertEqual(1, len(rows))
		self.assertEqual(self.project, rows[0]["project"])

	def test_list_progress_records_rejects_a_viewer_without_an_explicit_project_grant(self) -> None:
		"""Regresión directa de NXR-SEC-0001 (Bloque 19), aplicada al endpoint
		nuevo de este bloque."""
		self._create()
		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			list_progress_records({"project": self.project})

		frappe.set_user("Administrator")
		frappe.get_doc(
			{"doctype": "User Permission", "user": self.viewer, "allow": "Project", "for_value": self.project}
		).insert(ignore_permissions=True)
		frappe.set_user(self.viewer)
		rows = list_progress_records({"project": self.project})
		self.assertEqual(1, len(rows))
