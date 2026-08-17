"""Administración funcional de NEXORA contra Frappe/MariaDB real.

Requiere bench + MariaDB reales; no se pudo ejecutar en el entorno de esta
sesión (sin bench/Frappe/MariaDB — confirmado por
``ModuleNotFoundError: No module named 'frappe'`` al intentar importarlo
aquí, y por la ausencia de ``docker``/``bench`` documentada en el Bloque 46
de ``EXECUTION_STATE.md``). La lógica pura que sí se pudo ejercer sin
Frappe vive en ``test_administration_core.py`` (15 pruebas verdes
localmente) y la estructura del código en ``test_administration_contract.py``
(9 pruebas verdes localmente).

Cobertura pensada para la matriz mínima honesta de una pantalla que
administra usuarios y roles: permisos positivos/negativos por rol, la cuenta
técnica ``Administrator`` queda excluida de lectura y escritura, nunca se
puede desactivar ni desasignar el rol de Administrador del último
Administrador NEXORA activo, ninguna mutación toca un rol fuera del
conjunto de NEXORA, y cada mutación deja un ``NXR Audit Event`` real.
"""

from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.administration import service


def _key(prefix: str) -> str:
	return f"{prefix}-{uuid.uuid4().hex}"


def _ensure_user(email: str, roles: list[str]) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@", 1)[0],
				"enabled": 1,
				"send_welcome_email": 0,
				"roles": [{"role": role} for role in roles],
			}
		).insert(ignore_permissions=True)
	return email


class AdministrationTestBase(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		marker = uuid.uuid4().hex[:8]
		cls.admin = _ensure_user(f"nxr-admin-admin-{marker}@example.test", ["NEXORA Administrator"])
		cls.second_admin = _ensure_user(f"nxr-admin-admin2-{marker}@example.test", ["NEXORA Administrator"])
		cls.manager = _ensure_user(f"nxr-admin-manager-{marker}@example.test", ["NEXORA Finance Manager"])
		cls.operator = _ensure_user(f"nxr-admin-operator-{marker}@example.test", ["NEXORA Finance Operator"])
		cls.auditor = _ensure_user(f"nxr-admin-auditor-{marker}@example.test", ["NEXORA Auditor"])
		cls.plain_user = _ensure_user(f"nxr-admin-plain-{marker}@example.test", [])

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()


class TestViewPermissions(AdministrationTestBase):
	def test_administrator_can_list_users(self) -> None:
		frappe.set_user(self.admin)
		names = [row["name"] for row in service.list_users({})]
		self.assertIn(self.manager, names)

	def test_finance_manager_cannot_list_users(self) -> None:
		frappe.set_user(self.manager)
		with self.assertRaises(frappe.PermissionError):
			service.list_users({})

	def test_auditor_cannot_list_users(self) -> None:
		frappe.set_user(self.auditor)
		with self.assertRaises(frappe.PermissionError):
			service.list_users({})

	def test_plain_user_without_nexora_roles_cannot_list_users(self) -> None:
		frappe.set_user(self.plain_user)
		with self.assertRaises(frappe.PermissionError):
			service.list_users({})

	def test_listing_never_includes_the_technical_administrator_or_guest_accounts(self) -> None:
		frappe.set_user(self.admin)
		names = [row["name"] for row in service.list_users({})]
		self.assertNotIn("Administrator", names)
		self.assertNotIn("Guest", names)


class TestSetUserStatusPermissions(AdministrationTestBase):
	def test_finance_manager_cannot_change_user_status(self) -> None:
		frappe.set_user(self.manager)
		with self.assertRaises(frappe.PermissionError):
			service.set_user_status({"user": self.operator, "enabled": False})


class TestSetUserStatus(AdministrationTestBase):
	def test_administrator_can_disable_and_reenable_a_non_administrator_user(self) -> None:
		frappe.set_user(self.admin)
		service.set_user_status({"user": self.operator, "enabled": False})
		self.assertEqual(0, frappe.db.get_value("User", self.operator, "enabled"))
		service.set_user_status({"user": self.operator, "enabled": True})
		self.assertEqual(1, frappe.db.get_value("User", self.operator, "enabled"))

	def test_cannot_disable_own_session(self) -> None:
		frappe.set_user(self.admin)
		with self.assertRaises(frappe.ValidationError):
			service.set_user_status({"user": self.admin, "enabled": False})

	def test_cannot_disable_the_technical_administrator_account(self) -> None:
		frappe.set_user(self.admin)
		with self.assertRaises(frappe.ValidationError):
			service.set_user_status({"user": "Administrator", "enabled": False})

	def test_cannot_disable_the_last_active_nexora_administrator(self) -> None:
		frappe.set_user(self.admin)
		service.set_user_status({"user": self.second_admin, "enabled": False})
		try:
			with self.assertRaises(frappe.ValidationError):
				service.set_user_status({"user": self.admin, "enabled": False})
		finally:
			service.set_user_status({"user": self.second_admin, "enabled": True})

	def test_a_successful_status_change_is_audited(self) -> None:
		frappe.set_user(self.admin)
		service.set_user_status({"user": self.operator, "enabled": False})
		try:
			exists = frappe.db.exists(
				"NXR Audit Event",
				{
					"event_type": "nexora_user_status_changed",
					"reference_doctype": "User",
					"reference_name": self.operator,
				},
			)
			self.assertTrue(exists)
		finally:
			service.set_user_status({"user": self.operator, "enabled": True})


class TestSetUserRoles(AdministrationTestBase):
	def test_administrator_can_assign_and_revoke_a_nexora_role(self) -> None:
		frappe.set_user(self.admin)
		service.set_user_roles({"user": self.plain_user, "roles": ["NEXORA Project Viewer"]})
		self.assertTrue(
			frappe.db.exists("Has Role", {"parent": self.plain_user, "role": "NEXORA Project Viewer"})
		)
		service.set_user_roles({"user": self.plain_user, "roles": []})
		self.assertFalse(
			frappe.db.exists("Has Role", {"parent": self.plain_user, "role": "NEXORA Project Viewer"})
		)

	def test_rejects_a_role_outside_the_nexora_set(self) -> None:
		frappe.set_user(self.admin)
		with self.assertRaises(frappe.ValidationError):
			service.set_user_roles({"user": self.plain_user, "roles": ["System Manager"]})

	def test_never_touches_a_pre_existing_role_outside_the_nexora_set(self) -> None:
		frappe.set_user("Administrator")
		user_doc = frappe.get_doc("User", self.plain_user)
		if not frappe.db.exists("Has Role", {"parent": self.plain_user, "role": "Blogger"}):
			user_doc.append("roles", {"role": "Blogger"})
			user_doc.save(ignore_permissions=True)
		frappe.set_user(self.admin)
		try:
			service.set_user_roles({"user": self.plain_user, "roles": ["NEXORA Auditor"]})
			self.assertTrue(frappe.db.exists("Has Role", {"parent": self.plain_user, "role": "Blogger"}))
		finally:
			service.set_user_roles({"user": self.plain_user, "roles": []})

	def test_cannot_revoke_the_administrator_role_from_the_last_active_administrator(self) -> None:
		frappe.set_user(self.admin)
		service.set_user_roles({"user": self.second_admin, "roles": []})
		try:
			with self.assertRaises(frappe.ValidationError):
				service.set_user_roles({"user": self.admin, "roles": []})
		finally:
			service.set_user_roles({"user": self.second_admin, "roles": ["NEXORA Administrator"]})

	def test_cannot_manage_roles_of_the_technical_administrator_account(self) -> None:
		frappe.set_user(self.admin)
		with self.assertRaises(frappe.ValidationError):
			service.set_user_roles({"user": "Administrator", "roles": ["NEXORA Administrator"]})

	def test_a_successful_role_change_is_audited(self) -> None:
		frappe.set_user(self.admin)
		service.set_user_roles({"user": self.plain_user, "roles": ["NEXORA Auditor"]})
		try:
			exists = frappe.db.exists(
				"NXR Audit Event",
				{
					"event_type": "nexora_user_roles_changed",
					"reference_doctype": "User",
					"reference_name": self.plain_user,
				},
			)
			self.assertTrue(exists)
		finally:
			service.set_user_roles({"user": self.plain_user, "roles": []})


class TestListRecentActivity(AdministrationTestBase):
	def test_finance_manager_cannot_view_activity(self) -> None:
		frappe.set_user(self.manager)
		with self.assertRaises(frappe.PermissionError):
			service.list_recent_activity({})

	def test_administrator_sees_a_logged_mutation(self) -> None:
		frappe.set_user(self.admin)
		service.set_user_status({"user": self.operator, "enabled": False})
		try:
			rows = service.list_recent_activity({"limit": 50})
			self.assertTrue(any(row["reference_name"] == self.operator for row in rows))
		finally:
			service.set_user_status({"user": self.operator, "enabled": True})


if __name__ == "__main__":
	import unittest

	unittest.main()
