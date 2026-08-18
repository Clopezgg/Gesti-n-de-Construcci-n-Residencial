from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.file_manager import save_file

from nexora.directory.compliance_service import create_entity_compliance, transition_entity_compliance
from nexora.directory.service import create_entity, transition_entity
from nexora.financial.evidence import register_evidence, review_evidence
from nexora.financial.sources import create_fund_source
from nexora.inventory.service import create_warehouse
from nexora.purchases.order_service import create_order, get_order, list_orders, transition_order
from nexora.purchases.quotation_service import create_quotation, transition_quotation
from nexora.purchases.receipt_service import create_receipt, get_receipt, list_receipts, transition_receipt
from nexora.purchases.request_service import (
	create_purchase_request,
	get_purchase_request,
	list_purchase_requests,
	transition_purchase_request,
)
from nexora.purchases.service import create_supplier_profile, transition_supplier_profile


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


def _ensure_project() -> str:
	name = frappe.db.get_value("Project", {"project_name": "_Test NEXORA Receipt Project"}, "name")
	if name:
		return str(name)
	return str(
		frappe.get_doc(
			{"doctype": "Project", "project_name": "_Test NEXORA Receipt Project", "status": "Open"}
		)
		.insert(ignore_permissions=True)
		.name
	)


class TestReceiptIntegrationMariaDB(FrappeTestCase):
	"""NXR-COM-0010: `receipt_service._received_totals()`/`_update_po_status()` nunca se
	habían ejercido contra Frappe/MariaDB real (solo lógica pura en `test_receipt_core.py`).
	Reproduce el escenario exacto del defecto original: 90 recibido + 30 nuevo sobre una
	línea de 100 con 10% de tolerancia (antes aceptado sin error, ahora rechazado)."""

	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.project = _ensure_project()
		cls.cost_center = frappe.db.get_value("Cost Center", {"is_group": 0}, "name")
		cls.uom = frappe.db.get_value("UOM", {}, "name")
		cls.category = frappe.db.get_value("NXR Economic Category", {"active": 1}, "name")
		cls.item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
		if not cls.cost_center or not cls.uom or not cls.category or not cls.item_group:
			raise AssertionError("Faltan dependencias canónicas para probar recepciones")
		# `receipt_service.create_receipt` exige una bodega destino real
		# (`_ensure_link("NXR Warehouse", ..., required=True)`); este fixture nunca
		# la creaba — dormante hasta que los defectos previos de este mismo archivo
		# se corrigieron y el recorrido llegó por primera vez hasta este paso.
		cls.warehouse = create_warehouse(
			{"warehouse_name": f"Bodega recepción {uuid.uuid4().hex[:8]}", "project": cls.project}
		)["name"]
		# `inventory_bridge._goods_lines` exige `catalog_item` en cada línea "Goods"
		# antes de completar la recepción (para generar el movimiento de inventario
		# real) — opcional en solicitud/cotización/orden/recepción (fluye desde la
		# línea de la orden), pero obligatorio en este último paso. Este fixture
		# nunca lo fijaba; mismo patrón que los defectos anteriores de este archivo.
		cls.item = str(
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": f"_Test NEXORA Receipt Item {uuid.uuid4().hex[:8]}",
					"item_name": "Cemento",
					"item_group": cls.item_group,
					"stock_uom": cls.uom,
					"is_stock_item": 1,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		cls.operator = _ensure_user("nxr-receipt-operator@example.test", "NEXORA Finance Operator")
		cls.manager = _ensure_user("nxr-receipt-manager@example.test", "NEXORA Finance Manager")
		# DEC-008 (segregación de funciones): quien confirma la orden (`confirmed_by`,
		# usado como `requester` del compromiso) no puede ser quien la aprueba
		# (`approved_by`) — `_reserve_order`/`_commitment_payload` en
		# `financial_bridge.py` lo exige de verdad. Un solo gerente para ambos pasos
		# nunca se había ejercido contra Frappe real hasta corregir los defectos
		# anteriores de este mismo fixture.
		cls.approving_manager = _ensure_user(
			"nxr-receipt-approving-manager@example.test", "NEXORA Finance Manager"
		)
		cls.viewer = _ensure_user("nxr-receipt-viewer@example.test", "NEXORA Project Viewer")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _evidence(self) -> str:
		frappe.set_user(self.operator)
		file_doc = save_file(
			f"receipt-{uuid.uuid4().hex}.txt", b"NEXORA RECEIPT EVIDENCE", None, None, is_private=1
		)
		registered = register_evidence(
			{
				"project": self.project,
				"evidence_kind": "Other",
				"channel": "Other",
				"file_url": file_doc.file_url,
				"external_reference": f"RECEIPT-{uuid.uuid4().hex[:10]}",
				"idempotency_key": _key("receipt-evidence"),
			}
		)
		frappe.set_user(self.manager)
		review_evidence(str(registered["evidence"]), "Validated", _key("receipt-evidence-review"))
		return str(registered["evidence"])

	def _supplier(self) -> str:
		frappe.set_user(self.operator)
		entity = create_entity(
			{
				"entity_type": "Organization",
				"display_name": f"Proveedor recepción {uuid.uuid4().hex[:8]}",
				"identifiers": [
					{
						"identifier_type": "Internal Code",
						"identifier_value": f"SUP-{uuid.uuid4().hex}",
						"is_primary": 1,
					}
				],
				"idempotency_key": _key("receipt-entity"),
			}
		)
		frappe.set_user(self.manager)
		transition_entity(str(entity["name"]), "Active", _key("receipt-entity-active"))
		compliance = create_entity_compliance(
			{
				"entity": entity["name"],
				"compliance_type": "Supplier",
				"valid_from": "2026-01-01",
				"valid_until": "2027-12-31",
				"evidence": self._evidence(),
				"idempotency_key": _key("receipt-compliance"),
			}
		)
		transition_entity_compliance(
			str(compliance["compliance"]), "Current", _key("receipt-compliance-current")
		)
		supplier = create_supplier_profile(
			{
				"entity": entity["name"],
				"classification": "Goods",
				"valid_from": "2026-01-01",
				"valid_until": "2027-12-31",
				"compliance": compliance["compliance"],
				"idempotency_key": _key("receipt-supplier"),
			}
		)
		transition_supplier_profile(str(supplier["profile"]), "Active", _key("receipt-supplier-active"))
		return str(supplier["profile"])

	def _order(self, supplier: str) -> dict[str, object]:
		frappe.set_user(self.operator)
		request = create_purchase_request(
			{
				"request_date": "2026-07-24",
				"required_by": "2026-08-10",
				"project": self.project,
				"cost_center": self.cost_center,
				"responsible": self.operator,
				"priority": "High",
				"currency": "HNL",
				"justification": "Material para probar recepción acumulada.",
				"lines": [
					{
						"line_code": "MAT-001",
						"item_type": "Goods",
						"description": "Cemento",
						"quantity": "100",
						"uom": self.uom,
						"estimated_unit_rate": "50",
						"economic_category": self.category,
					}
				],
				"idempotency_key": _key("receipt-request"),
			}
		)
		transition_purchase_request(str(request["request"]), "Submitted", _key("receipt-request-submit"))
		transition_purchase_request(str(request["request"]), "In Review", _key("receipt-request-review"))
		frappe.set_user(self.manager)
		transition_purchase_request(str(request["request"]), "Approved", _key("receipt-request-approved"))

		frappe.set_user(self.manager)
		quotation = create_quotation(
			{
				"purchase_request": request["request"],
				"supplier_profile": supplier,
				"currency": "HNL",
				"quotation_date": "2026-07-24",
				"valid_until": "2026-09-30",
				"lines": [
					{
						"line_code": "MAT-001",
						"item_type": "Goods",
						"description": "Cemento",
						"quantity": "100",
						"uom": self.uom,
						"unit_rate": "50",
					}
				],
				"idempotency_key": _key("receipt-quotation"),
			}
		)
		transition_quotation(str(quotation["quotation"]), "Submitted", _key("receipt-quote-submit"))
		transition_quotation(
			str(quotation["quotation"]), "Accepted", _key("receipt-quote-accept"), reason="Única opción"
		)

		# NXR-SEC-0002 (#202, ya en main): `create_purchase_order`/`submit_purchase_order`
		# se restringieron a MANAGER_ROLES — un Operador financiero ya no puede crear ni
		# confirmar una orden. Este fixture seguía usando `self.operator` para ambos pasos
		# (nunca actualizado tras #202, nunca ejercido contra Frappe/MariaDB real hasta
		# ahora), lo que rechazaba `create_order` con `PermissionError` antes de llegar al
		# escenario real que esta prueba busca cubrir.
		frappe.set_user(self.manager)
		# `financial_bridge._ensure_source()` exige una fuente de fondos real antes de
		# aprobar la orden (NXR-COM-0006) — `fund_source` es opcional al crear (ver
		# corrección de `nxr_purchase_order.json` en este mismo bloque) pero obligatorio
		# al llegar a `Approved`. Este fixture nunca la creaba.
		fund_source = create_fund_source(
			{
				"idempotency_key": _key("receipt-fund"),
				"source_name": f"Fuente recepción {uuid.uuid4().hex[:8]}",
				"channel": "Remittance",
				"project": self.project,
				"currency": "HNL",
				"original_amount": 100000,
				"exchange_rate": 1,
				"origin_or_sender": "Remitente CI recepción",
				"custodian": self.manager,
			}
		)["fund_source"]
		order = create_order(
			{
				"purchase_request": request["request"],
				"supplier_quotation": quotation["quotation"],
				"supplier_profile": supplier,
				"currency": "HNL",
				"fund_source": fund_source,
				"lines": [
					{
						"line_code": "MAT-001",
						"item_type": "Goods",
						"catalog_item": self.item,
						"description": "Cemento",
						"quantity": "100",
						"uom": self.uom,
						"unit_rate": "50",
					}
				],
				"idempotency_key": _key("receipt-order"),
			}
		)
		transition_order(str(order["name"]), "Confirmed", _key("receipt-order-confirmed"))
		frappe.set_user(self.approving_manager)
		transition_order(str(order["name"]), "Approved", _key("receipt-order-approved"))
		transition_order(str(order["name"]), "Sent", _key("receipt-order-sent"))
		return order

	def test_cumulative_over_receipt_beyond_tolerance_is_rejected_and_po_status_reflects_real_totals(
		self,
	) -> None:
		supplier = self._supplier()
		order = self._order(supplier)
		po_line = order["lines"][0]["name"]

		frappe.set_user(self.operator)
		first = create_receipt(
			{
				"purchase_order": order["name"],
				"warehouse": self.warehouse,
				"lines": [
					{
						"purchase_order_line": po_line,
						"quantity": "90",
					}
				],
				"idempotency_key": _key("receipt-first"),
			}
		)
		self.assertEqual("Draft", first["status"])
		# `sync_goods_receipt_inventory` (hook de `on_update`) llama
		# `inventory.service.transition_stock_transaction` al completar la
		# recepción, que exige `submit_stock_transaction` (MANAGER_ROLES) — más
		# estricto que la propia transición de la recepción (OPERATOR_ROLES). Un
		# Operador nunca podía completar una recepción real hasta este fixture.
		frappe.set_user(self.manager)
		transition_receipt(str(first["name"]), "Completed", _key("receipt-first-complete"))
		frappe.set_user(self.operator)
		self.assertEqual(
			"Sent",
			frappe.db.get_value("NXR Purchase Order", order["name"], "status"),
			"Con 90 de 100 recibido la orden no debía marcarse completada.",
		)

		with self.assertRaisesRegex(frappe.ValidationError, "excede la tolerancia"):
			create_receipt(
				{
					"purchase_order": order["name"],
					"warehouse": self.warehouse,
					"lines": [
						{
							"purchase_order_line": po_line,
							"quantity": "30",
						}
					],
					"idempotency_key": _key("receipt-second-over"),
				}
			)

		second = create_receipt(
			{
				"purchase_order": order["name"],
				"warehouse": self.warehouse,
				"lines": [
					{
						"purchase_order_line": po_line,
						"quantity": "15",
					}
				],
				"idempotency_key": _key("receipt-second-ok"),
			}
		)
		frappe.set_user(self.manager)
		transition_receipt(str(second["name"]), "Completed", _key("receipt-second-complete"))
		self.assertEqual(
			"Completed",
			frappe.db.get_value("NXR Purchase Order", order["name"], "status"),
			"Con 105 de 100 (dentro de tolerancia) la orden debía marcarse completada.",
		)
		self.assertTrue(
			frappe.db.exists(
				"NXR Audit Event",
				{"reference_doctype": "NXR Goods Receipt", "reference_name": second["name"]},
			)
		)

	def test_receipt_without_a_warehouse_is_rejected_and_nothing_is_created(self) -> None:
		"""GP-04 (Bloque 80): "recepción sin bodega" quedaba como la única de tres
		pruebas negativas de este golden path sin verificar en ningún sentido —
		`create_receipt` exige `_ensure_link("NXR Warehouse", ..., required=True)`
		antes de cualquier mutación (ni siquiera se llega a `start_idempotency`),
		pero nunca se había ejercido contra Frappe/MariaDB real."""
		supplier = self._supplier()
		order = self._order(supplier)
		po_line = order["lines"][0]["name"]

		frappe.set_user(self.operator)
		key = _key("receipt-no-warehouse")
		with self.assertRaisesRegex(frappe.ValidationError, "bodega destino"):
			create_receipt(
				{
					"purchase_order": order["name"],
					"lines": [{"purchase_order_line": po_line, "quantity": "10"}],
					"idempotency_key": key,
				}
			)
		# El rechazo ocurre antes de la primera mutación: ni la clave de
		# idempotencia ni ningún documento deben quedar registrados.
		self.assertFalse(frappe.db.exists("NXR Idempotency Record", key))
		self.assertFalse(frappe.db.exists("NXR Goods Receipt", {"idempotency_key": key}))

	def test_get_and_list_purchase_documents_reject_a_viewer_without_an_explicit_project_grant(
		self,
	) -> None:
		"""NXR-SEC-0001 (Bloque 19): regresión real — `get_order`/`list_orders`,
		`get_purchase_request`/`list_purchase_requests` y `get_receipt`/
		`list_receipts` deben resolver el permiso contra el proyecto real del
		documento, no bastar con el rol amplio "NEXORA Project Viewer"."""
		supplier = self._supplier()
		order = self._order(supplier)
		request = str(order["purchase_request"])
		frappe.set_user(self.operator)
		receipt = create_receipt(
			{
				"purchase_order": order["name"],
				"warehouse": self.warehouse,
				"lines": [{"purchase_order_line": order["lines"][0]["name"], "quantity": "10"}],
				"idempotency_key": _key("receipt-scoping"),
			}
		)

		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			get_order(order["name"])
		with self.assertRaises(frappe.PermissionError):
			list_orders(project=self.project)
		with self.assertRaises(frappe.PermissionError):
			get_purchase_request(request)
		with self.assertRaises(frappe.PermissionError):
			list_purchase_requests(project=self.project)
		with self.assertRaises(frappe.PermissionError):
			get_receipt(receipt["name"])
		with self.assertRaises(frappe.PermissionError):
			list_receipts(purchase_order=order["name"])

		frappe.set_user("Administrator")
		grant = frappe.get_doc(
			{"doctype": "User Permission", "user": self.viewer, "allow": "Project", "for_value": self.project}
		).insert(ignore_permissions=True)
		try:
			frappe.set_user(self.viewer)
			self.assertEqual(order["name"], get_order(order["name"])["name"])
			self.assertTrue(any(row["name"] == order["name"] for row in list_orders(project=self.project)))
			self.assertEqual(request, get_purchase_request(request)["request"])
			self.assertTrue(
				any(row["request"] == request for row in list_purchase_requests(project=self.project))
			)
			self.assertEqual(receipt["name"], get_receipt(receipt["name"])["name"])
			self.assertTrue(
				any(row["name"] == receipt["name"] for row in list_receipts(purchase_order=order["name"]))
			)
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("User Permission", grant.name, ignore_permissions=True)


if __name__ == "__main__":
	import unittest

	unittest.main()
