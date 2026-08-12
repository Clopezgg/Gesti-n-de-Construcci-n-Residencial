"""NXR-SEC-0001 (Bloque 19): último tramo real — inventario contra Frappe/MariaDB.

Requiere bench + MariaDB reales. Cobertura mínima honesta: creación real de un
movimiento de inventario, transición Draft→Completed, lectura real por
proyecto vía `get_stock_transaction`/`list_stock_transactions` y su rechazo a
un usuario sin acceso al proyecto — regresión directa del hallazgo original de
NXR-SEC-0001, la única de las catorce funciones que quedaba sin ejercer por
falta de fixtures reales de `Item`/`NXR Warehouse`.

**Defecto real encontrado al construir este fixture, no supuesto:** `NXR
Warehouse` exige `require_service_write()` desde que existe (Bloque 13) pero
ningún módulo de servicio abría esa puerta — confirmado en rojo real de CI al
intentar insertar una bodega directamente (`ValidationError: Este documento
solo puede escribirse mediante un servicio transaccional NEXORA`). Sin bodega
real, ningún movimiento de inventario podía registrarse jamás en producción.
Corregido con `inventory.service.create_warehouse`, ejercida aquí también.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.inventory.service import (
	create_stock_transaction,
	create_warehouse,
	get_stock_transaction,
	list_stock_transactions,
	transition_stock_transaction,
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


class TestInventoryIntegrationMariaDB(FrappeTestCase):
	def setUp(self) -> None:
		frappe.set_user("Administrator")
		marker = uuid.uuid4().hex[:10]
		self.project = str(
			frappe.get_doc(
				{"doctype": "Project", "project_name": f"_Test NEXORA Inventory {marker}", "status": "Open"}
			)
			.insert(ignore_permissions=True)
			.name
		)
		self.item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
		if not self.item_group:
			raise AssertionError("No se encontró ningún Item Group hoja en el sitio de prueba")
		self.uom = frappe.db.get_value("UOM", {}, "name")
		if not self.uom:
			raise AssertionError("No se encontró ninguna UOM en el sitio de prueba")
		self.operator = _ensure_user(
			f"nxr-inventory-operator-{marker}@example.test", "NEXORA Finance Operator"
		)
		self.viewer = _ensure_user(f"nxr-inventory-viewer-{marker}@example.test", "NEXORA Project Viewer")
		frappe.set_user(self.operator)
		self.warehouse = str(
			create_warehouse({"warehouse_name": f"_Test Warehouse {marker}", "project": self.project})["name"]
		)
		frappe.set_user("Administrator")
		self.item = str(
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": f"_TEST-NXR-INV-{marker}",
					"item_name": f"_Test NEXORA Inventory Item {marker}",
					"item_group": self.item_group,
					"stock_uom": self.uom,
					"is_stock_item": 1,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _create(self, **overrides) -> dict:
		payload = {
			"transaction_type": "Receipt",
			"project": self.project,
			"warehouse": self.warehouse,
			"transaction_date": frappe.utils.today(),
			"lines": [
				{
					"item": self.item,
					"warehouse": self.warehouse,
					"quantity": "10",
					"unit_rate": "25.50",
				}
			],
			"idempotency_key": _key("stock-transaction"),
		}
		payload.update(overrides)
		frappe.set_user(self.operator)
		return create_stock_transaction(payload)

	def test_create_warehouse_records_a_real_active_document(self) -> None:
		frappe.set_user(self.operator)
		created = create_warehouse(
			{"warehouse_name": f"_Test Warehouse {_key('extra')}", "project": self.project}
		)
		doc = frappe.get_doc("NXR Warehouse", created["name"])
		self.assertTrue(bool(doc.active))
		self.assertEqual(self.project, doc.project)
		self.assertTrue(
			frappe.db.exists(
				"NXR Audit Event",
				{
					"event_type": "warehouse_created",
					"reference_doctype": "NXR Warehouse",
					"reference_name": doc.name,
				},
			)
		)

	def test_direct_warehouse_write_outside_the_service_is_rejected(self) -> None:
		"""Regresión directa del defecto real encontrado: `NXR Warehouse` debe
		seguir bloqueando cualquier escritura que no pase por
		`inventory.service.create_warehouse`."""
		with self.assertRaisesRegex(frappe.ValidationError, "servicio transaccional NEXORA"):
			frappe.get_doc(
				{"doctype": "NXR Warehouse", "warehouse_name": f"_Test Direct {_key('x')}", "active": 1}
			).insert(ignore_permissions=True)

	def test_create_records_a_real_document_and_transitions_to_completed(self) -> None:
		result = self._create()
		doc = frappe.get_doc("NXR Stock Transaction", result["name"])
		self.assertEqual("Draft", doc.status)
		self.assertEqual(self.project, doc.project)
		self.assertEqual(Decimal("255.00"), Decimal(str(doc.total_amount)))

		frappe.set_user(self.operator)
		completed = transition_stock_transaction(
			result["name"], "Completed", _key("stock-transaction-complete")
		)
		self.assertEqual("Completed", completed["status"])

	def test_invalid_transition_is_rejected_by_the_real_state_machine(self) -> None:
		result = self._create()
		frappe.set_user(self.operator)
		transition_stock_transaction(result["name"], "Completed", _key("stock-transaction-complete-2"))
		# `assert_stock_transition` lanza `PurchaseValidationError`, pero
		# `transition_stock_transaction` la traduce con `frappe.throw(...)` (sin
		# clase explícita) al `frappe.ValidationError` genérico — mismo patrón que
		# el resto del módulo, nunca la excepción interna cruda.
		with self.assertRaises(frappe.ValidationError):
			transition_stock_transaction(
				result["name"], "Cancelled", _key("stock-transaction-cancel"), "tarde"
			)

	def test_get_and_list_stock_transactions_reject_a_viewer_without_an_explicit_project_grant(self) -> None:
		"""NXR-SEC-0001 (Bloque 19): última pieza del hallazgo original — regresión real."""
		result = self._create()
		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			get_stock_transaction(result["name"])
		with self.assertRaises(frappe.PermissionError):
			list_stock_transactions(project=self.project)

		frappe.set_user("Administrator")
		grant = frappe.get_doc(
			{"doctype": "User Permission", "user": self.viewer, "allow": "Project", "for_value": self.project}
		).insert(ignore_permissions=True)
		try:
			frappe.set_user(self.viewer)
			snapshot = get_stock_transaction(result["name"])
			self.assertEqual(result["name"], snapshot["name"])
			rows = list_stock_transactions(project=self.project)
			self.assertTrue(any(row["name"] == result["name"] for row in rows))
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("User Permission", grant.name, ignore_permissions=True)


if __name__ == "__main__":
	import unittest

	unittest.main()
