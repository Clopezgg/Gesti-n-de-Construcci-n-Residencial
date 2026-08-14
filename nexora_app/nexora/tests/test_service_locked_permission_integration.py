from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

# Cierre de deuda (auditoría final): estos 23 DocTypes tenían require_service_write()
# como único candado real — el permiso de DocType declarado seguía permitiendo
# create a roles NEXORA en permlevel 0, una puerta sin uso real (Frappe rechazaba
# antes de llegar a insertar por el hook), pero real en el sentido de que la propia
# capa de permisos de Frappe (frappe.has_permission / botón «+ Nuevo» / API create)
# la consideraba abierta. Se corrigió create=0 en el DocType JSON para permlevel 0,
# sin tocar require_service_write() (defensa en profundidad se mantiene) ni ningún
# otro campo de permiso. Esta prueba verifica la protección NUEVA que aporta el
# fix: frappe.has_permission ahora también rechaza, no solo el hook — algo que no
# se podía probar antes porque el permiso declarado lo permitía.
#
# write es distinto: NXR Fund Source es la única excepción real. A diferencia de
# los otros 22, su before_save() no llama a require_service_write() — antes de
# validar, deja pasar un doc.save() normal desde el formulario estándar cuando el
# usuario marca request_cancellation, y antes de que ese save complete,
# _cancel_fund_source() aplica su propia autorización real con
# require_action("cancel_source"). Quitarle write rompía dos pruebas reales de
# integración (test_manager_cancels_unused_income_from_standard_form,
# test_income_with_related_outflow_cannot_be_cancelled en
# test_financial_integration.py) con un frappe.PermissionError genérico antes de
# que el controlador llegara a decidir nada — ver la misma nota en
# test_app_contract.py::test_service_locked_doctypes_do_not_leak_raw_create_or_write_permission.
WRITE_PERMITTED_DOCTYPES = frozenset({"NXR Fund Source"})

SERVICE_LOCKED_DOCTYPES = (
	"NXR AI Provider",
	"NXR Budget",
	"NXR Channel Account",
	"NXR Channel Credential",
	"NXR Commitment",
	"NXR Contract",
	"NXR Contract Amendment",
	"NXR Contract Estimate",
	"NXR Contractor Profile",
	"NXR Fund Source",
	"NXR Goods Receipt",
	"NXR Integration",
	"NXR Monthly Close",
	"NXR Notification",
	"NXR Operation",
	"NXR Progress Record",
	"NXR Purchase Order",
	"NXR Purchase Request",
	"NXR Quality Check",
	"NXR Stock Transaction",
	"NXR Supplier Profile",
	"NXR Supplier Quotation",
	"NXR Warehouse",
)

NEXORA_ROLES = (
	"NEXORA Administrator",
	"NEXORA Finance Manager",
	"NEXORA Finance Operator",
)


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


class TestServiceLockedPermissionIntegration(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.users = {
			role: _ensure_user(f"nxr-permcheck-{role.lower().replace(' ', '-')}@example.test", role)
			for role in NEXORA_ROLES
		}

	def tearDown(self) -> None:
		frappe.set_user("Administrator")

	def test_no_nexora_role_has_raw_create_on_service_locked_doctypes(self) -> None:
		"""Verificación en vivo, no solo lectura estática del JSON (ver
		test_app_contract.py::test_service_locked_doctypes_do_not_leak_raw_create_or_write_permission
		para la contraparte sin Frappe): con el motor de permisos real cargado,
		ningún rol NEXORA debe poder crear directamente estos DocTypes. Antes del
		fix, frappe.has_permission("create") devolvía True aquí para al menos un
		rol en cada uno de estos 23 DocTypes — el candado real
		(require_service_write) solo actuaba después, en el hook before_insert,
		nunca a nivel de permiso declarado."""
		failures: list[str] = []
		for doctype in SERVICE_LOCKED_DOCTYPES:
			for role, user in self.users.items():
				frappe.set_user(user)
				if frappe.has_permission(doctype, "create", user=user):
					failures.append(f"{doctype}: {role} tiene permiso de creación declarado")
		frappe.set_user("Administrator")
		self.assertEqual([], failures, "\n".join(failures))

	def test_write_permission_is_closed_except_for_the_one_justified_exception(self) -> None:
		"""write no tiene la misma tolerancia cero que create: NXR Fund Source
		necesita write real para su flujo de anulación desde el formulario
		estándar (ver la nota extensa junto a WRITE_PERMITTED_DOCTYPES). Todos
		los demás deben seguir sin write declarado."""
		failures: list[str] = []
		for doctype in SERVICE_LOCKED_DOCTYPES:
			expected_write = doctype in WRITE_PERMITTED_DOCTYPES
			for role, user in self.users.items():
				frappe.set_user(user)
				has_write = bool(frappe.has_permission(doctype, "write", user=user))
				if has_write != expected_write:
					failures.append(f"{doctype}: {role} write={has_write}, se esperaba {expected_write}")
		frappe.set_user("Administrator")
		self.assertEqual([], failures, "\n".join(failures))

	def test_raw_desk_style_insert_is_rejected_by_frappes_own_permission_engine(self) -> None:
		"""Complementa test_direct_canonical_source_creation_is_rejected
		(test_financial_integration.py), que llama con ignore_permissions=True y
		por eso nunca ejerce esta capa. Aquí se omite ignore_permissions a
		propósito: sin él, Frappe debe rechazar por permiso ANTES de llegar al
		hook before_insert (que también rechazaría, pero con otro motivo). Solo
		se prueba NXR Fund Source como representante: construir un documento
		válido de los 23 DocTypes exigiría los fixtures completos de cada
		módulo, y el permiso ya se probó exhaustivamente arriba sin necesitar
		un documento válido."""
		frappe.set_user(self.users["NEXORA Finance Operator"])
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				{
					"doctype": "NXR Fund Source",
					"source_code": "PERMCHECK-DIRECT",
					"source_name": "Intento directo sin ignore_permissions",
					"channel": "Cash",
					"source_date": frappe.utils.today(),
					"currency": "HNL",
					"original_amount": 100,
					"exchange_rate": 1,
					"origin_or_sender": "Prueba de permiso",
					"custodian": self.users["NEXORA Finance Operator"],
					"status": "Active",
				}
			).insert()
