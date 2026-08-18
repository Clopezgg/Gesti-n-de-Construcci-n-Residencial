from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import frappe

from nexora.inventory.service import create_stock_transaction, create_warehouse, transition_stock_transaction


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


def _ensure_project(project_name: str) -> str:
	existing = frappe.db.get_value("Project", {"project_name": project_name}, "name")
	if existing:
		return str(existing)
	return str(
		frappe.get_doc({"doctype": "Project", "project_name": project_name, "status": "Open"})
		.insert(ignore_permissions=True)
		.name
	)


def run() -> dict[str, object]:
	"""`_assert_no_negative_balance` (`inventory/service.py`) bloquea cada `NXR
	Warehouse` involucrada con `FOR UPDATE` antes de agregar el saldo real —
	mismo principio que el lock de línea de presupuesto (Bloque 77) y el de
	fuente de fondos, pero un tercer mecanismo de bloqueo distinto (por bodega,
	no por una sola fila de saldo) que nunca se había ejercido bajo concurrencia
	real, solo secuencial (`test_inventory_integration.py`).
	"""
	marker = uuid.uuid4().hex[:12]
	project = _ensure_project(f"_Test Inventory Concurrency {marker}")
	manager = _ensure_user(f"nxr-invconc-manager-{marker}@example.test", "NEXORA Finance Manager")
	operator = _ensure_user(f"nxr-invconc-operator-{marker}@example.test", "NEXORA Finance Operator")

	item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
	uom = frappe.db.get_value("UOM", {}, "name")
	if not item_group or not uom:
		raise AssertionError("No leaf Item Group or UOM found to run the probe against.")

	frappe.set_user(manager)  # nosemgrep
	warehouse = str(
		create_warehouse({"warehouse_name": f"_Test Inventory Concurrency {marker}", "project": project})["name"]
	)
	frappe.set_user("Administrator")  # nosemgrep
	item = str(
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": f"_TEST-NXR-INVCONC-{marker}",
				"item_name": f"_Test Inventory Concurrency Item {marker}",
				"item_group": item_group,
				"stock_uom": uom,
				"is_stock_item": 1,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)

	def _transaction(transaction_type: str, quantity: int) -> dict:
		return create_stock_transaction(
			{
				"transaction_type": transaction_type,
				"project": project,
				"warehouse": warehouse,
				"transaction_date": frappe.utils.today(),
				"lines": [{"item": item, "warehouse": warehouse, "quantity": str(quantity), "unit_rate": "10"}],
				"idempotency_key": f"invconc-{transaction_type.lower()}-{marker}-{uuid.uuid4().hex[:8]}",
			}
		)

	frappe.set_user(operator)  # nosemgrep
	receipt = _transaction("Receipt", 10)["name"]
	frappe.set_user(manager)  # nosemgrep
	transition_stock_transaction(
		transaction=receipt,
		status="Completed",
		idempotency_key=f"invconc-receipt-complete-{marker}",
	)

	frappe.set_user(operator)  # nosemgrep
	drafts = [_transaction("Consumption", 8)["name"] for _ in range(2)]
	# Fixture data must be visible to two independent MariaDB worker connections.
	frappe.db.commit()  # nosemgrep
	site = frappe.local.site
	sites_path = frappe.local.sites_path
	barrier = threading.Barrier(2)

	def worker(index: int) -> str:
		frappe.init(site=site, sites_path=sites_path)
		frappe.connect()
		# Test-only identity switch inside an isolated worker connection.
		frappe.set_user(manager)  # nosemgrep
		try:
			barrier.wait(timeout=20)
			transition_stock_transaction(
				transaction=drafts[index],
				status="Completed",
				idempotency_key=f"invconc-consume-complete-{marker}-{index}",
			)
			# Commit the worker transaction to prove row-lock serialization.
			frappe.db.commit()  # nosemgrep
			return "executed"
		except Exception as exc:  # noqa: BLE001 -- clasifica cualquier resultado real de la carrera
			frappe.db.rollback()
			return (
				"denied_negative"
				if "quedaría con inventario negativo" in str(exc)
				else f"unexpected:{type(exc).__name__}:{exc}"
			)
		finally:
			frappe.destroy()

	with ThreadPoolExecutor(max_workers=2) as pool:
		results = sorted(pool.map(worker, (0, 1)))

	# Restore the test actor before reading the resulting balance.
	frappe.set_user(manager)  # nosemgrep
	rows = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(CASE
			WHEN t.transaction_type = 'Receipt' THEN l.quantity
			WHEN t.transaction_type = 'Consumption' THEN -l.quantity
			ELSE 0 END), 0) balance_qty
		FROM `tabNXR Stock Transaction Line` l
		INNER JOIN `tabNXR Stock Transaction` t ON t.name = l.parent
		WHERE t.status = 'Completed' AND l.item = %s AND l.warehouse = %s
		""",
		(item, warehouse),
	)
	balance = Decimal(str(rows[0][0]))
	if results != ["denied_negative", "executed"] or balance != Decimal("2"):
		raise AssertionError({"results": results, "balance": str(balance)})
	return {"ok": True, "results": results, "balance": str(balance)}
