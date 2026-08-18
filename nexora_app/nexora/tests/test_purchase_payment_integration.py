from __future__ import annotations

import uuid
from collections.abc import Mapping

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.file_manager import save_file

from nexora.directory.compliance_service import create_entity_compliance, transition_entity_compliance
from nexora.directory.service import create_entity, transition_entity
from nexora.financial.core import money
from nexora.financial.db import commitment_outstanding
from nexora.financial.evidence import register_evidence, review_evidence
from nexora.financial.sources import create_fund_source
from nexora.inventory.service import create_warehouse
from nexora.purchases.financial_bridge import pay_purchase_order
from nexora.purchases.order_service import create_order, transition_order
from nexora.purchases.quotation_service import create_quotation, transition_quotation
from nexora.purchases.receipt_service import create_receipt, transition_receipt
from nexora.purchases.request_service import create_purchase_request, transition_purchase_request
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
	name = frappe.db.get_value("Project", {"project_name": "_Test NEXORA Payment Project"}, "name")
	if name:
		return str(name)
	return str(
		frappe.get_doc(
			{"doctype": "Project", "project_name": "_Test NEXORA Payment Project", "status": "Open"}
		)
		.insert(ignore_permissions=True)
		.name
	)


class TestPurchasePaymentIntegrationMariaDB(FrappeTestCase):
	"""`financial_bridge.pay_purchase_order` solo tenía cobertura de contrato
	(`test_purchase_financial_bridge_contract.py`: existe, está protegido con
	`@frappe.whitelist`, nunca se ejecutó contra Frappe/MariaDB real). Es el último
	paso del golden path de compras (Solicitud → Cotización → Orden → Recepción →
	Pago) y el de mayor riesgo financiero — ejecuta sobre el mismo motor de
	compromisos que el resto del sistema — y no tenía ninguna prueba que
	comprobara, contra una base real, que el tope de "recibido", el tope de saldo
	del compromiso y la idempotencia realmente se sostienen cuando se ejecutan.
	"""

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
			raise AssertionError("Faltan dependencias canónicas para probar el pago de compras")
		cls.warehouse = create_warehouse(
			{"warehouse_name": f"Bodega pago {uuid.uuid4().hex[:8]}", "project": cls.project}
		)["name"]
		cls.item = str(
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": f"_Test NEXORA Payment Item {uuid.uuid4().hex[:8]}",
					"item_name": "Cemento",
					"item_group": cls.item_group,
					"stock_uom": cls.uom,
					"is_stock_item": 1,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		cls.operator = _ensure_user("nxr-payment-operator@example.test", "NEXORA Finance Operator")
		cls.manager = _ensure_user("nxr-payment-manager@example.test", "NEXORA Finance Manager")
		# DEC-008 (segregación de funciones): quien confirma la orden no puede ser
		# quien la aprueba (mismo requisito ya ejercido en test_receipt_integration.py).
		cls.approving_manager = _ensure_user(
			"nxr-payment-approving-manager@example.test", "NEXORA Finance Manager"
		)
		cls.viewer = _ensure_user("nxr-payment-viewer@example.test", "NEXORA Project Viewer")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _evidence(self) -> str:
		frappe.set_user(self.operator)
		file_doc = save_file(
			f"payment-{uuid.uuid4().hex}.txt", b"NEXORA PAYMENT EVIDENCE", None, None, is_private=1
		)
		registered = register_evidence(
			{
				"project": self.project,
				"evidence_kind": "Other",
				"channel": "Other",
				"file_url": file_doc.file_url,
				"external_reference": f"PAYMENT-{uuid.uuid4().hex[:10]}",
				"idempotency_key": _key("payment-evidence"),
			}
		)
		frappe.set_user(self.manager)
		review_evidence(str(registered["evidence"]), "Validated", _key("payment-evidence-review"))
		return str(registered["evidence"])

	def _supplier(self) -> str:
		frappe.set_user(self.operator)
		entity = create_entity(
			{
				"entity_type": "Organization",
				"display_name": f"Proveedor pago {uuid.uuid4().hex[:8]}",
				"identifiers": [
					{
						"identifier_type": "Internal Code",
						"identifier_value": f"SUP-{uuid.uuid4().hex}",
						"is_primary": 1,
					}
				],
				"idempotency_key": _key("payment-entity"),
			}
		)
		frappe.set_user(self.manager)
		transition_entity(str(entity["name"]), "Active", _key("payment-entity-active"))
		compliance = create_entity_compliance(
			{
				"entity": entity["name"],
				"compliance_type": "Supplier",
				"valid_from": "2026-01-01",
				"valid_until": "2027-12-31",
				"evidence": self._evidence(),
				"idempotency_key": _key("payment-compliance"),
			}
		)
		transition_entity_compliance(
			str(compliance["compliance"]), "Current", _key("payment-compliance-current")
		)
		supplier = create_supplier_profile(
			{
				"entity": entity["name"],
				"classification": "Goods",
				"valid_from": "2026-01-01",
				"valid_until": "2027-12-31",
				"compliance": compliance["compliance"],
				"idempotency_key": _key("payment-supplier"),
			}
		)
		transition_supplier_profile(str(supplier["profile"]), "Active", _key("payment-supplier-active"))
		return str(supplier["profile"])

	def _order(self, supplier: str, *, send: bool = True) -> dict[str, object]:
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
				"justification": "Material para probar el pago de orden de compra.",
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
				"idempotency_key": _key("payment-request"),
			}
		)
		transition_purchase_request(str(request["request"]), "Submitted", _key("payment-request-submit"))
		transition_purchase_request(str(request["request"]), "In Review", _key("payment-request-review"))
		frappe.set_user(self.manager)
		transition_purchase_request(str(request["request"]), "Approved", _key("payment-request-approved"))

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
				"idempotency_key": _key("payment-quotation"),
			}
		)
		transition_quotation(str(quotation["quotation"]), "Submitted", _key("payment-quote-submit"))
		transition_quotation(
			str(quotation["quotation"]), "Accepted", _key("payment-quote-accept"), reason="Única opción"
		)

		frappe.set_user(self.manager)
		fund_source = create_fund_source(
			{
				"idempotency_key": _key("payment-fund"),
				"source_name": f"Fuente pago {uuid.uuid4().hex[:8]}",
				"channel": "Remittance",
				"project": self.project,
				"currency": "HNL",
				"original_amount": 100000,
				"exchange_rate": 1,
				"origin_or_sender": "Remitente CI pago",
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
				"idempotency_key": _key("payment-order"),
			}
		)
		transition_order(str(order["name"]), "Confirmed", _key("payment-order-confirmed"))
		frappe.set_user(self.approving_manager)
		transition_order(str(order["name"]), "Approved", _key("payment-order-approved"))
		if send:
			transition_order(str(order["name"]), "Sent", _key("payment-order-sent"))
		return order

	def _receive(self, order: Mapping[str, object], po_line: str, quantity: str) -> dict[str, object]:
		frappe.set_user(self.operator)
		receipt = create_receipt(
			{
				"purchase_order": order["name"],
				"warehouse": self.warehouse,
				"lines": [{"purchase_order_line": po_line, "quantity": quantity}],
				"idempotency_key": _key("payment-receipt"),
			}
		)
		frappe.set_user(self.manager)
		transition_receipt(str(receipt["name"]), "Completed", _key("payment-receipt-complete"))
		frappe.set_user(self.operator)
		return receipt

	def test_payment_respects_received_and_outstanding_caps_and_marks_the_commitment_executed(self) -> None:
		supplier = self._supplier()
		order = self._order(supplier)
		po_line = order["lines"][0]["name"]
		commitment = frappe.db.get_value("NXR Purchase Order", order["name"], "financial_commitment")
		self.assertTrue(commitment, "La orden aprobada debe tener un compromiso financiero reservado.")
		self.assertEqual(money("5000"), commitment_outstanding(commitment))

		# Nada recibido todavía: cualquier pago debe rechazarse, sin importar que el
		# compromiso tenga saldo de sobra.
		with self.assertRaisesRegex(frappe.ValidationError, "recibido"):
			pay_purchase_order(
				{
					"purchase_order": order["name"],
					"idempotency_key": _key("payment-too-early"),
					"amount_hnl": "100",
				}
			)

		self._receive(order, po_line, "60")
		first = pay_purchase_order(
			{
				"purchase_order": order["name"],
				"idempotency_key": _key("payment-first"),
				"amount_hnl": "2000",
				"economic_category": self.category,
			}
		)
		self.assertEqual(commitment, first["commitment"])
		self.assertEqual("Partially Executed", frappe.db.get_value("NXR Commitment", commitment, "status"))
		self.assertEqual(
			money("2000"),
			money(frappe.db.get_value("NXR Purchase Order", order["name"], "commitment_executed_hnl")),
		)
		self.assertEqual(money("3000"), commitment_outstanding(commitment))
		self.assertTrue(
			frappe.db.exists(
				"NXR Audit Event",
				{"reference_doctype": "NXR Purchase Order", "reference_name": order["name"]},
			)
		)

		self._receive(order, po_line, "40")
		self.assertEqual("Completed", frappe.db.get_value("NXR Purchase Order", order["name"], "status"))
		second = pay_purchase_order(
			{
				"purchase_order": order["name"],
				"idempotency_key": _key("payment-second"),
				"amount_hnl": "3000",
				"economic_category": self.category,
			}
		)
		self.assertEqual(commitment, second["commitment"])
		self.assertEqual("Executed", frappe.db.get_value("NXR Commitment", commitment, "status"))
		self.assertEqual(money("0"), commitment_outstanding(commitment))
		self.assertEqual(
			money("5000"),
			money(frappe.db.get_value("NXR Purchase Order", order["name"], "commitment_executed_hnl")),
		)

		# El compromiso ya se ejecutó por completo: un pago adicional, por mínimo que
		# sea, no puede generar una segunda afectación financiera.
		with self.assertRaisesRegex(frappe.ValidationError, "saldo disponible"):
			pay_purchase_order(
				{
					"purchase_order": order["name"],
					"idempotency_key": _key("payment-overpay"),
					"amount_hnl": "1",
				}
			)

	def test_payment_retry_with_the_same_key_replays_the_original_result(self) -> None:
		supplier = self._supplier()
		order = self._order(supplier)
		po_line = order["lines"][0]["name"]
		commitment = frappe.db.get_value("NXR Purchase Order", order["name"], "financial_commitment")
		self._receive(order, po_line, "100")

		key = _key("payment-retry")
		payload = {
			"purchase_order": order["name"],
			"idempotency_key": key,
			"amount_hnl": "5000",
			"economic_category": self.category,
		}
		first = pay_purchase_order(dict(payload))
		self.assertEqual(money("0"), commitment_outstanding(commitment))

		# Un reintento con la misma clave — doble clic, corte de red — debe devolver
		# exactamente la misma respuesta, no ejecutar el compromiso una segunda vez.
		second = pay_purchase_order(dict(payload))
		self.assertEqual(first, second)
		self.assertEqual(money("0"), commitment_outstanding(commitment))
		self.assertEqual(
			money("5000"),
			money(frappe.db.get_value("NXR Purchase Order", order["name"], "commitment_executed_hnl")),
		)

	def test_payment_rejects_an_order_that_has_not_been_sent_and_a_viewer_role(self) -> None:
		supplier = self._supplier()
		order = self._order(supplier, send=False)
		frappe.set_user(self.operator)
		with self.assertRaisesRegex(frappe.ValidationError, "enviada o completada"):
			pay_purchase_order(
				{
					"purchase_order": order["name"],
					"idempotency_key": _key("payment-not-sent"),
					"amount_hnl": "100",
				}
			)

		transition_order(str(order["name"]), "Sent", _key("payment-late-send"))
		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			pay_purchase_order(
				{
					"purchase_order": order["name"],
					"idempotency_key": _key("payment-viewer-denied"),
					"amount_hnl": "100",
				}
			)


if __name__ == "__main__":
	import unittest

	unittest.main()
