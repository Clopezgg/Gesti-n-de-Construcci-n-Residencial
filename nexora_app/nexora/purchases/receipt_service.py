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
from nexora.permissions import require_action, require_project_access
from nexora.purchases.receipt_core import (
	assert_receipt_transition,
	compute_po_completion_status,
	validate_receipt_lines,
)
from nexora.purchases.request_core import PurchaseValidationError, money


def _required(data: Mapping[str, Any], fieldname: str, message: str) -> str:
	value = str(data.get(fieldname) or "").strip()
	if not value:
		frappe.throw(_(message))
	return value


def _lock(name: str) -> Any:
	table = frappe.qb.DocType("NXR Goods Receipt")
	rows = (frappe.qb.from_(table).select(table.name).where(table.name == name).for_update()).run()
	if not rows:
		frappe.throw(_("La recepción no existe."))
	return frappe.get_doc("NXR Goods Receipt", name)


def _ensure_link(doctype: str, name: str | None, label: str, *, required: bool = True) -> str | None:
	value = str(name or "").strip()
	if not value:
		if required:
			frappe.throw(_("La recepción requiere {0}.").format(label))
		return None
	if not frappe.db.exists(doctype, value):
		frappe.throw(_("El valor de {0} no existe.").format(label))
	return value


def _received_totals(po_line_refs: list[str]) -> dict[str, Any]:
	"""Cantidad aceptada acumulada por línea de orden, excluyendo recepciones anuladas.

	Reemplaza una lectura de una sola fila (`frappe.db.get_value` sin `SUM`) que nunca
	acumulaba recepciones previas de la misma línea (NXR-COM-0010).
	"""
	unique_refs = sorted({ref for ref in po_line_refs if ref})
	if not unique_refs:
		return {}
	rows = frappe.get_all(
		"NXR Goods Receipt Line",
		filters={"purchase_order_line": ["in", unique_refs]},
		fields=["purchase_order_line", "accepted_quantity", "parent"],
	)
	if not rows:
		return {}
	parent_names = sorted({row.parent for row in rows})
	cancelled = set(
		frappe.get_all(
			"NXR Goods Receipt",
			filters={"name": ["in", parent_names], "status": "Cancelled"},
			pluck="name",
		)
	)
	totals: dict[str, Any] = {}
	for row in rows:
		if row.parent in cancelled:
			continue
		totals[row.purchase_order_line] = money(
			totals.get(row.purchase_order_line, 0) + money(row.accepted_quantity)
		)
	return totals


def _normalized_lines(
	lines: list[Mapping[str, Any]],
	po_name: str,
) -> list[dict[str, Any]]:
	po_doc = frappe.get_doc("NXR Purchase Order", po_name)
	po_lines: dict[str, Any] = {}
	for pol in po_doc.lines:
		po_lines[pol.name] = pol
	for pol in po_doc.lines:
		if pol.line_code not in po_lines:
			po_lines[pol.line_code] = pol
	received_totals = _received_totals([str(raw.get("purchase_order_line") or "").strip() for raw in lines])
	prepared: list[dict[str, Any]] = []
	for index, raw in enumerate(lines, start=1):
		line = dict(raw)
		line_code = str(line.get("line_code") or f"{index:03d}").strip()
		po_line_ref = str(line.get("purchase_order_line") or "").strip()
		if not po_line_ref:
			frappe.throw(_("Cada línea de recepción requiere referencia a línea de orden."))
		po_line = po_lines.get(po_line_ref)
		if not po_line:
			frappe.throw(_("La línea de orden {0} no existe.").format(po_line_ref))
		ordered_qty = money(po_line.quantity)
		prev_received = received_totals.get(po_line_ref, money(0))
		quantity = money(line.get("quantity"))
		if quantity <= 0:
			frappe.throw(_("La línea {0} requiere cantidad positiva.").format(line_code))
		rejected = money(line.get("rejected_quantity"))
		if rejected < 0:
			frappe.throw(_("La cantidad rechazada no puede ser negativa."))
		accepted = money(quantity - rejected)
		if accepted < 0:
			frappe.throw(_("La cantidad aceptada no puede ser negativa."))
		amount = money(accepted * money(po_line.unit_rate))
		prepared.append(
			{
				"line_code": line_code,
				"purchase_order_line": po_line_ref,
				"item_type": po_line.item_type,
				"catalog_item": po_line.catalog_item,
				"description": po_line.description,
				"ordered_quantity": str(ordered_qty),
				"previously_received": str(prev_received),
				"quantity": str(quantity),
				"rejected_quantity": str(rejected),
				"accepted_quantity": str(accepted),
				"uom": po_line.uom,
				"unit_rate": po_line.unit_rate,
				"amount": str(amount),
				"economic_category": po_line.economic_category,
				"notes": line.get("notes"),
			}
		)
	try:
		validate_receipt_lines(
			prepared,
			[
				{"name": pol.name, "quantity": pol.quantity, "line_code": pol.line_code}
				for pol in po_doc.lines
			],
			money(po_line.tolerance_percentage) if hasattr(po_line, "tolerance_percentage") else None,
		)
	except PurchaseValidationError as exc:
		frappe.throw(_(str(exc)))
	return prepared


def _snapshot(doc: Any) -> dict[str, Any]:
	return {
		"name": doc.name,
		"document_number": doc.document_number,
		"status": doc.status,
		"purchase_order": doc.purchase_order,
		"supplier_profile": doc.supplier_profile,
		"supplier_entity": doc.supplier_entity,
		"project": doc.project,
		"cost_center": doc.cost_center,
		"currency": doc.currency,
		"receipt_date": doc.receipt_date,
		"notes": doc.notes,
		"total_amount": doc.total_amount,
		"lines": [
			{
				"name": line.name,
				"line_code": line.line_code,
				"purchase_order_line": line.purchase_order_line,
				"item_type": line.item_type,
				"catalog_item": line.catalog_item,
				"description": line.description,
				"ordered_quantity": line.ordered_quantity,
				"previously_received": line.previously_received,
				"quantity": line.quantity,
				"rejected_quantity": line.rejected_quantity,
				"accepted_quantity": line.accepted_quantity,
				"uom": line.uom,
				"unit_rate": line.unit_rate,
				"amount": line.amount,
				"economic_category": line.economic_category,
			}
			for line in doc.lines
		],
	}


def _total_from_lines(prepared: list[dict[str, Any]]) -> str:
	return str(sum(money(line["amount"]) for line in prepared))


@frappe.whitelist(methods=["POST"])
def create_receipt(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("create_purchase_request")
	data = parse_payload(payload)
	purchase_order = _ensure_link("NXR Purchase Order", data.get("purchase_order"), "orden de compra")
	po_doc = frappe.get_doc("NXR Purchase Order", purchase_order)
	if po_doc.status not in {"Sent", "Approved", "Confirmed"}:
		frappe.throw(_("La orden de compra debe estar enviada para recibir."))
	supplier_profile = _ensure_link(
		"NXR Supplier Profile", data.get("supplier_profile") or po_doc.supplier_profile, "perfil de proveedor"
	)
	supplier_entity = po_doc.supplier_entity
	currency = _ensure_link("Currency", data.get("currency") or po_doc.currency, "moneda")
	lines = _normalized_lines(list(data.get("lines") or []), purchase_order)
	total = _total_from_lines(lines)
	key = _required(data, "idempotency_key", "La recepción requiere clave de idempotencia.")
	normalized = {**data, "supplier_entity": supplier_entity, "lines": lines, "total_amount": total}
	fingerprint = canonical_payload_hash(normalized)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		number, sequence = issue_document_number("NXR Goods Receipt", key)
		with service_write():
			doc = frappe.get_doc(
				{
					"doctype": "NXR Goods Receipt",
					"document_number": number,
					"status": "Draft",
					"purchase_order": purchase_order,
					"supplier_profile": supplier_profile,
					"supplier_entity": supplier_entity,
					"project": po_doc.project,
					"cost_center": po_doc.cost_center,
					"currency": currency,
					"receipt_date": data.get("receipt_date") or frappe.utils.getdate(),
					"notes": data.get("notes"),
					"total_amount": total,
					"lines": lines,
					"evidence": _ensure_link(
						"NXR Evidence", data.get("evidence"), "evidencia", required=False
					),
					"idempotency_key": key,
					"payload_hash": fingerprint,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
		link_sequence(sequence, doc.name)
		result = _snapshot(doc)
		audit("goods_receipt_created", "NXR Goods Receipt", doc.name, fingerprint, correlation_id, result)
		complete_idempotency(idem, "NXR Goods Receipt", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def transition_receipt(
	receipt: str, status: str, idempotency_key: str, reason: str | None = None
) -> dict[str, Any]:
	target = str(status or "").strip().title()
	require_action("submit_purchase_request")
	payload = {"receipt": receipt, "status": target, "reason": str(reason or "").strip()}
	fingerprint = canonical_payload_hash(payload)
	correlation_id = correlation(payload)
	point = savepoint()
	try:
		idem, cached = start_idempotency(idempotency_key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		doc = _lock(receipt)
		try:
			assert_receipt_transition(str(doc.status), target)
		except PurchaseValidationError as exc:
			frappe.throw(_(str(exc)))
		if target == "Cancelled" and not payload["reason"]:
			frappe.throw(_("La cancelación de recepción requiere motivo."))
		with service_write():
			doc.status = target
			if target == "Completed":
				doc.received_by = frappe.session.user
			doc.save(ignore_permissions=True)
		if target == "Completed":
			_update_po_status(doc.purchase_order)
		result = _snapshot(doc)
		audit(
			"goods_receipt_transitioned", "NXR Goods Receipt", doc.name, fingerprint, correlation_id, result
		)
		complete_idempotency(idem, "NXR Goods Receipt", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


def _update_po_status(po_name: str) -> None:
	po = frappe.get_doc("NXR Purchase Order", po_name)
	po_line_names = [pol.name for pol in po.lines]
	received_totals = _received_totals(po_line_names)
	order_lines = [{"name": pol.name, "quantity": pol.quantity} for pol in po.lines]
	po.status = compute_po_completion_status(order_lines, received_totals)
	with service_write():
		po.save(ignore_permissions=True)


@frappe.whitelist(methods=["GET"])
def get_receipt(receipt: str) -> dict[str, Any]:
	# NXR-SEC-0001 (Bloque 19): permiso contra el proyecto real del documento, no
	# uno declarado por el cliente.
	doc = frappe.get_doc("NXR Goods Receipt", receipt)
	require_project_access(doc.project, action="read_purchases")
	return _snapshot(doc)


@frappe.whitelist(methods=["GET"])
def list_receipts(
	purchase_order: str | None = None, status: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
	if purchase_order:
		project = frappe.db.get_value("NXR Purchase Order", purchase_order, "project")
		require_project_access(project, action="read_purchases")
	else:
		require_project_access(None, action="read_purchases")
	filters: dict[str, Any] = {}
	if purchase_order:
		filters["purchase_order"] = purchase_order
	if status:
		filters["status"] = status
	rows = frappe.get_all(
		"NXR Goods Receipt",
		filters=filters,
		fields=["name"],
		order_by="modified desc",
		limit=min(max(int(limit or 100), 1), 500),
	)
	return [_snapshot(frappe.get_doc("NXR Goods Receipt", row.name)) for row in rows]
