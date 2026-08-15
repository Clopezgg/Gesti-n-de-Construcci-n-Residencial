from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.financial.context import service_write
from nexora.financial.core import canonical_payload_hash
from nexora.financial.db import (
	audit,
	complete_idempotency,
	correlation,
	issue_document_number,
	link_sequence,
	parse_payload,
	rollback,
	savepoint,
	start_idempotency,
)
from nexora.inventory.core import (
	INCOMING_STOCK_TRANSACTION_TYPES,
	OUTGOING_STOCK_TRANSACTION_TYPES,
	STOCK_TRANSACTION_TYPES,
	PurchaseValidationError,
	assert_stock_transition,
	money,
	quantity,
	validate_item_balance,
)
from nexora.permissions import require_action, require_project_access


def _required(data: Mapping[str, Any], fieldname: str, message: str) -> str:
	value = str(data.get(fieldname) or "").strip()
	if not value:
		frappe.throw(_(message))
	return value


def _lock(name: str) -> Any:
	table = frappe.qb.DocType("NXR Stock Transaction")
	rows = (frappe.qb.from_(table).select(table.name).where(table.name == name).for_update()).run()
	if not rows:
		frappe.throw(_("El movimiento de inventario no existe."))
	return frappe.get_doc("NXR Stock Transaction", name)


def _assert_no_negative_balance(doc: Any) -> None:
	"""Un movimiento de salida (ver `OUTGOING_STOCK_TRANSACTION_TYPES`) no puede
	dejar el saldo de ningún ítem/bodega en negativo — mismo invariante que ya
	protege los fondos (`no saldo negativo`). Hasta esta corrección, el único
	lugar que calculaba el saldo real por ítem/bodega era el panel de
	"inventario crítico" del dashboard (`dashboard/inventory_query.py::critical_inventory`),
	que solo lo reporta después de que ya ocurrió — nunca lo impedía; una
	salida podía dejar cualquier ítem en negativo sin que nada lo rechazara.

	Bloquea primero cada `NXR Warehouse` involucrada (orden estable, mismo
	criterio que `financial/db.py::lock_sources`) antes de agregar: no hay una
	sola fila de "saldo" que bloquear como en fondos, así que se serializa por
	bodega para que dos transiciones concurrentes sobre el mismo ítem no lean
	el mismo saldo desactualizado."""

	if doc.transaction_type not in OUTGOING_STOCK_TRANSACTION_TYPES:
		return
	pairs = {(line.item, line.warehouse) for line in doc.lines}
	if not pairs:
		return
	items = sorted({item for item, _warehouse in pairs})
	warehouses = sorted({warehouse for _item, warehouse in pairs})
	warehouse_table = frappe.qb.DocType("NXR Warehouse")
	(
		frappe.qb.from_(warehouse_table)
		.select(warehouse_table.name)
		.where(warehouse_table.name.isin(warehouses))
		.orderby(warehouse_table.name)
		.for_update()
	).run()
	rows = frappe.db.sql(
		"""
		SELECT l.item, l.warehouse, COALESCE(SUM(CASE
			WHEN t.transaction_type IN %(incoming)s THEN l.quantity
			WHEN t.transaction_type IN %(outgoing)s THEN -l.quantity
			ELSE 0 END), 0) balance_qty
		FROM `tabNXR Stock Transaction Line` l
		INNER JOIN `tabNXR Stock Transaction` t ON t.name = l.parent
		WHERE t.status = 'Completed' AND l.item IN %(items)s AND l.warehouse IN %(warehouses)s
		GROUP BY l.item, l.warehouse
		""",
		{
			"incoming": tuple(INCOMING_STOCK_TRANSACTION_TYPES),
			"outgoing": tuple(OUTGOING_STOCK_TRANSACTION_TYPES),
			"items": items,
			"warehouses": warehouses,
		},
		as_dict=True,
	)
	current_balance = {(row.item, row.warehouse): quantity(row.balance_qty) for row in rows}
	outgoing_by_pair: dict[tuple[str, str], Any] = {}
	for line in doc.lines:
		key = (line.item, line.warehouse)
		outgoing_by_pair[key] = outgoing_by_pair.get(key, quantity(0)) + quantity(line.quantity)
	for (item, warehouse), outgoing_qty in outgoing_by_pair.items():
		try:
			validate_item_balance(
				item, warehouse, current_balance.get((item, warehouse), quantity(0)), outgoing_qty
			)
		except PurchaseValidationError as exc:
			frappe.throw(_(str(exc)))


def _ensure_link(doctype: str, name: str | None, label: str, *, required: bool = True) -> str | None:
	value = str(name or "").strip()
	if not value:
		if required:
			frappe.throw(_("El movimiento requiere {0}.").format(label))
		return None
	if not frappe.db.exists(doctype, value):
		frappe.throw(_("El valor de {0} no existe.").format(label))
	return value


def _normalized_lines(
	lines: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
	prepared: list[dict[str, Any]] = []
	for index, raw in enumerate(lines, start=1):
		line = dict(raw)
		line_code = str(line.get("line_code") or f"{index:03d}").strip()
		item = _ensure_link("Item", line.get("item"), "artículo")
		warehouse = _ensure_link("NXR Warehouse", line.get("warehouse"), "bodega")
		if not frappe.db.get_value("NXR Warehouse", warehouse, "active"):
			frappe.throw(_("La bodega {0} está inactiva.").format(warehouse))
		qty = quantity(line.get("quantity"))
		if qty <= 0:
			frappe.throw(_("La línea {0} requiere cantidad positiva.").format(line_code))
		rate = money(line.get("unit_rate"))
		if rate < 0:
			frappe.throw(_("La línea {0} no admite precio negativo.").format(line_code))
		amount = money(qty * rate)
		prepared.append(
			{
				"line_code": line_code,
				"item": item,
				"warehouse": warehouse,
				"quantity": str(qty),
				"unit_rate": str(rate),
				"amount": str(amount),
				"batch_no": line.get("batch_no"),
				"reference_doctype": line.get("reference_doctype"),
				"reference_name": line.get("reference_name"),
				"notes": line.get("notes"),
			}
		)
	return prepared


def _snapshot(doc: Any) -> dict[str, Any]:
	return {
		"name": doc.name,
		"document_number": doc.document_number,
		"status": doc.status,
		"transaction_type": doc.transaction_type,
		"project": doc.project,
		"transaction_date": doc.transaction_date,
		"notes": doc.notes,
		"total_amount": doc.total_amount,
		"lines": [
			{
				"name": line.name,
				"line_code": line.line_code,
				"item": line.item,
				"warehouse": line.warehouse,
				"quantity": line.quantity,
				"unit_rate": line.unit_rate,
				"amount": line.amount,
				"batch_no": line.batch_no,
				"reference_doctype": line.reference_doctype,
				"reference_name": line.reference_name,
			}
			for line in doc.lines
		],
	}


def _total(lines: list[dict[str, Any]]) -> str:
	return str(sum(money(l["amount"]) for l in lines))


@frappe.whitelist(methods=["POST"])
def create_warehouse(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""`NXR Warehouse` exige `require_service_write()` en `before_insert`/
	`before_save` (mismo bloqueo que cualquier otro doctype de dominio
	sensible) pero, hasta esta función, ningún módulo de servicio abría esa
	puerta: ni un Administrador podía crear una bodega real por ninguna vía —
	sin bodega, ningún movimiento de inventario puede registrarse, porque
	`create_stock_transaction`/`_normalized_lines` exigen una `NXR Warehouse`
	real y activa. Mismo patrón que `conversation.channels.whatsapp.
	link_channel_account` (doctype de referencia simple, sin numeración
	documental propia): `service_write()` + auditoría real, sin la maquinaria
	de idempotencia que sí necesitan los documentos financieros.
	"""
	data = parse_payload(payload)
	require_action("create_purchase_request")
	warehouse_name = _required(data, "warehouse_name", "La bodega requiere nombre.")
	project = _ensure_link("Project", data.get("project"), "proyecto", required=False)
	correlation_id = correlation(data)
	with service_write():
		doc = frappe.get_doc(
			{
				"doctype": "NXR Warehouse",
				"warehouse_name": warehouse_name,
				"project": project,
				"location": data.get("location"),
				"active": 1,
				"notes": data.get("notes"),
			}
		).insert(ignore_permissions=True)
	result = {"name": doc.name, "warehouse_name": doc.warehouse_name, "active": bool(doc.active)}
	audit(
		"warehouse_created",
		"NXR Warehouse",
		doc.name,
		canonical_payload_hash({"warehouse_name": warehouse_name, "project": project}),
		correlation_id,
		result,
	)
	return result


@frappe.whitelist(methods=["POST"])
def create_stock_transaction(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("create_purchase_request")
	data = parse_payload(payload)
	transaction_type = str(data.get("transaction_type") or "").strip().title()
	if transaction_type not in STOCK_TRANSACTION_TYPES:
		frappe.throw(_("Tipo de movimiento de inventario no válido."))
	project = _ensure_link("Project", data.get("project"), "proyecto", required=False)
	warehouse = _ensure_link("NXR Warehouse", data.get("warehouse"), "bodega", required=False)
	lines = _normalized_lines(list(data.get("lines") or []))
	if not lines:
		frappe.throw(_("El movimiento requiere al menos una línea."))
	total_amount = _total(lines)
	key = _required(data, "idempotency_key", "El movimiento requiere clave de idempotencia.")
	normalized = {**data, "transaction_type": transaction_type, "lines": lines, "total_amount": total_amount}
	fingerprint = canonical_payload_hash(normalized)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		number, sequence = issue_document_number("NXR Stock Transaction", key)
		with service_write():
			doc = frappe.get_doc(
				{
					"doctype": "NXR Stock Transaction",
					"document_number": number,
					"status": "Draft",
					"transaction_type": transaction_type,
					"project": project,
					"warehouse": warehouse,
					"transaction_date": data.get("transaction_date") or frappe.utils.getdate(),
					"notes": data.get("notes"),
					"total_amount": total_amount,
					"lines": lines,
					"evidence": _ensure_link(
						"NXR Evidence", data.get("evidence"), "evidencia", required=False
					),
					"contract": _ensure_link(
						"NXR Contract", data.get("contract"), "contrato", required=False
					),
					"purchase_order": _ensure_link(
						"NXR Purchase Order", data.get("purchase_order"), "orden de compra", required=False
					),
					"goods_receipt": _ensure_link(
						"NXR Goods Receipt", data.get("goods_receipt"), "recepción", required=False
					),
					"idempotency_key": key,
					"payload_hash": fingerprint,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
		link_sequence(sequence, doc.name)
		result = _snapshot(doc)
		audit(
			"stock_transaction_created",
			"NXR Stock Transaction",
			doc.name,
			fingerprint,
			correlation_id,
			result,
		)
		complete_idempotency(idem, "NXR Stock Transaction", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def transition_stock_transaction(
	transaction: str, status: str, idempotency_key: str, reason: str | None = None
) -> dict[str, Any]:
	target = str(status or "").strip().title()
	require_action("submit_purchase_request")
	payload = {"transaction": transaction, "status": target, "reason": str(reason or "").strip()}
	fingerprint = canonical_payload_hash(payload)
	correlation_id = correlation(payload)
	point = savepoint()
	try:
		idem, cached = start_idempotency(idempotency_key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		doc = _lock(transaction)
		try:
			assert_stock_transition(str(doc.status), target)
		except PurchaseValidationError as exc:
			frappe.throw(_(str(exc)))
		if target == "Cancelled" and not payload["reason"]:
			frappe.throw(_("La cancelación de movimiento requiere motivo."))
		if target == "Completed":
			_assert_no_negative_balance(doc)
		with service_write():
			doc.status = target
			doc.save(ignore_permissions=True)
		result = _snapshot(doc)
		audit(
			"stock_transaction_transitioned",
			"NXR Stock Transaction",
			doc.name,
			fingerprint,
			correlation_id,
			result,
		)
		complete_idempotency(idem, "NXR Stock Transaction", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["GET"])
def get_stock_transaction(transaction: str) -> dict[str, Any]:
	# NXR-SEC-0001 (Bloque 19): permiso contra el proyecto real del documento, no
	# uno declarado por el cliente.
	doc = frappe.get_doc("NXR Stock Transaction", transaction)
	require_project_access(doc.project, action="read_purchases")
	return _snapshot(doc)


@frappe.whitelist(methods=["GET"])
def list_stock_transactions(
	project: str | None = None, transaction_type: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
	require_project_access(project, action="read_purchases")
	filters: dict[str, Any] = {}
	if project:
		filters["project"] = project
	if transaction_type:
		filters["transaction_type"] = transaction_type
	rows = frappe.get_all(
		"NXR Stock Transaction",
		filters=filters,
		fields=["name"],
		order_by="modified desc",
		limit=min(max(int(limit or 100), 1), 500),
	)
	return [_snapshot(frappe.get_doc("NXR Stock Transaction", row.name)) for row in rows]
