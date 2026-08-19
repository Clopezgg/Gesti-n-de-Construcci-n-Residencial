from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.close.canonical_weekly import (
	calculate_weekly_close,
	correct_weekly_close,
	list_weekly_closes,
	save_weekly_close,
)


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


class TestCanonicalWeeklyCloseMariaDB(FrappeTestCase):
	def setUp(self) -> None:
		super().setUp()
		frappe.set_user("Administrator")
		marker = uuid.uuid4().hex[:10]
		self.project = str(
			frappe.get_doc(
				{
					"doctype": "Project",
					"project_name": f"_Test NEXORA Weekly V3 {marker}",
					"status": "Open",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		self.manager = _user(
			f"nxr-weekly-v3-manager-{marker}@example.test",
			"NEXORA Finance Manager",
		)
		self.viewer = _user(
			f"nxr-weekly-v3-viewer-{marker}@example.test",
			"NEXORA Project Viewer",
		)
		self.week_end = frappe.utils.today()
		self.week_start = frappe.utils.add_days(self.week_end, -6)

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def test_public_v3_close_is_idempotent_versioned_and_correctable(self) -> None:
		frappe.set_user(self.manager)
		base = {
			"project": self.project,
			"week_start": self.week_start,
			"week_end": self.week_end,
			"comments": "Cierre canónico v3 de aceptación",
		}
		preview = calculate_weekly_close(base)
		self.assertEqual("nexora-analytics-v3", preview["engine_version"])
		self.assertEqual(64, len(preview["snapshot_hash"]))
		self.assertEqual(self.project, preview["project"])

		payload = {**base, "idempotency_key": _key("weekly-v3")}
		first = save_weekly_close(payload)
		self.assertEqual(first, save_weekly_close(payload))
		self.assertEqual("nexora-analytics-v3", first["engine_version"])
		self.assertRegex(first["document_number"], r"^\d{12}$")
		doc = frappe.get_doc("NXR Weekly Close", first["weekly_close"])
		self.assertEqual("nexora-analytics-v3", doc.engine_version)
		self.assertEqual(preview["snapshot_hash"], doc.snapshot_hash)

		correction = correct_weekly_close(
			{
				**base,
				"weekly_close": first["weekly_close"],
				"correction_reason": "Conciliación posterior documentada",
				"idempotency_key": _key("weekly-v3-correction"),
			}
		)
		self.assertEqual("Correction", correction["status"])
		self.assertEqual("nexora-analytics-v3", correction["engine_version"])
		self.assertNotEqual(first["weekly_close"], correction["weekly_close"])
		correction_doc = frappe.get_doc("NXR Weekly Close", correction["weekly_close"])
		self.assertEqual(first["weekly_close"], correction_doc.correction_of)

		history = list_weekly_closes({"project": self.project, "page": 1, "page_size": 10})
		names = {row.name for row in history["rows"]}
		self.assertIn(first["weekly_close"], names)
		self.assertIn(correction["weekly_close"], names)
		self.assertEqual(2, history["pagination"]["total"])

	def test_a_viewer_can_calculate_and_list_with_project_permission_but_never_save_or_correct(
		self,
	) -> None:
		"""`close.service.calculate_weekly_close`/`list_weekly_closes` exigen
		`view_closings` (`ACCESS_ROLES`, incluye a "NEXORA Project Viewer" — con
		permiso explícito de proyecto, que ningún rol ACCESS_ROLES se salta:
		`_has_explicit_project_permission` solo exime a Administrator y a quien
		tenga `view_all_projects`, que Project Viewer no tiene). `save_weekly_close`/
		`correct_weekly_close` exigen en cambio `save_closing` (`MANAGER_ROLES`) —
		un cierre real, financiero, que bloquea el período no puede quedar a un
		clic de un rol de solo lectura. El hermano mensual
		(`test_monthly_close_canonical_integration.py::
		test_a_viewer_can_list_but_cannot_create_transition_or_correct`) ya
		prueba esta misma asimetría para `close.monthly_canonical`; este archivo
		nunca la había probado para `close.canonical_weekly`, pese a compartir
		exactamente el mismo mecanismo `require_action`/`require_project_access`."""
		frappe.set_user(self.manager)
		base = {
			"project": self.project,
			"week_start": self.week_start,
			"week_end": self.week_end,
			"comments": "Cierre para probar el límite de permisos del visor",
		}
		saved = save_weekly_close({**base, "idempotency_key": _key("weekly-for-viewer")})

		frappe.set_user(self.viewer)
		# Sin permiso explícito de proyecto, "NEXORA Project Viewer" tampoco puede
		# calcular ni listar — mismo patrón que ya prueba el cierre mensual.
		with self.assertRaises(frappe.PermissionError):
			calculate_weekly_close(base)
		with self.assertRaises(frappe.PermissionError):
			list_weekly_closes({"project": self.project})

		frappe.set_user("Administrator")
		grant = frappe.get_doc(
			{"doctype": "User Permission", "user": self.viewer, "allow": "Project", "for_value": self.project}
		).insert(ignore_permissions=True)
		try:
			frappe.set_user(self.viewer)
			preview = calculate_weekly_close(base)
			self.assertEqual(self.project, preview["project"])
			listed = list_weekly_closes({"project": self.project})
			self.assertIn(saved["weekly_close"], {row.name for row in listed["rows"]})

			# El permiso de proyecto basta para "view_closings", pero
			# "save_closing" sigue exigiendo Gerente financiero o Administrador.
			with self.assertRaises(frappe.PermissionError):
				save_weekly_close({**base, "idempotency_key": _key("weekly-viewer-save-denied")})
			with self.assertRaises(frappe.PermissionError):
				correct_weekly_close(
					{
						**base,
						"weekly_close": saved["weekly_close"],
						"correction_reason": "Motivo con más de diez caracteres",
						"idempotency_key": _key("weekly-viewer-correct-denied"),
					}
				)
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("User Permission", grant.name, ignore_permissions=True)
