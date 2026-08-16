from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _
from frappe.utils import now_datetime

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
from nexora.purchases.order_core import (
	PurchaseValidationError,
	assert_order_transition,
	money,
	order_line_amounts,
)
from nexora.purchases.request_core import PURCHASE_ITEM_TYPES


def _required(data: Mapping[str, Any], fieldname: str, message: str) -> str:
	value = str(data.get(fieldname) or "").strip()
	if not value:
		frappe.throw(_(message))
	return value


def _lock(name: str) -> Any:
	table = frappe.qb.DocType("NXR Purchase Order")
	rows = (frappe.qb.from_(table).select(table.name).where(table.name == name).for_update()).run()
	if not rows:
		frappe.throw(_("La orden de compra no existe."))
	return frappe.get_doc("NXR Purchase Order", name)


def _ensure_link(doctype: str, name: str | None, label: str, *, required: bool = True) -> str | None:
	value = str(name or "").strip()
	if not value:
		if required:
			frappe.throw(_("La orden requiere {0}.").format(label))
		return None
	if not frappe.db.exists(doctype, value):
		frappe.throw(_("El valor de {0} no existe.").format(label))
	return value


def _resolve_supplier(supplier_profile: str) -> str:
	if not frappe.db.exists("NXR Supplier Profile", supplier_profile):
		frappe.throw(_("El perfil de proveedor no existe."))
	status = frappe.db.get_value("NXR Supplier Profile", supplier_profile, "status")
	if status != "Active":
		frappe.throw(_("El perfil de proveedor debe estar activo."))
	entity = frappe.db.get_value("NXR Supplier Profile", supplier_profile, "entity")
	return str(entity)


def _normalized_lines(
	lines: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
	prepared: list[dict[str, Any]] = []
	for index, raw in enumerate(lines, start=1):
		line = dict(raw)
		line_code = str(line.get("line_code") or f"{index:03d}").strip()
		item_type = str(line.get("item_type") or "Goods").strip().title()
		if item_type not in PURCHASE_ITEM_TYPES:
			frappe.throw(_("El tipo de línea debe ser Goods o Service."))
		catalog_item = _ensure_link("Item", line.get("catalog_item"), "artículo de catálogo", required=False)
		uom = _ensure_link("UOM", line.get("uom"), "unidad de medida")
		description = _required(line, "description", "Cada línea requiere descripción.")
		quantity = money(line.get("quantity"))
		if quantity <= 0:
			frappe.throw(_("La línea {0} requiere cantidad positiva.").format(line_code))
		unit_rate = money(line.get("unit_rate"))
		if unit_rate < 0:
			frappe.throw(_("La línea {0} no admite precio negativo.").format(line_code))
		amount = money(quantity * unit_rate)
		charge_amount = money(line.get("charge_amount"))
		tax_rate = money(line.get("tax_rate"))
		tax_amount = money(amount * tax_rate / 100) if tax_rate else money(line.get("tax_amount"))
		discount_rate = money(line.get("discount_rate"))
		discount_amount = (
			money(amount * discount_rate / 100) if discount_rate else money(line.get("discount_amount"))
		)
		net_amount = money(amount + charge_amount + tax_amount - discount_amount)
		if net_amount < 0:
			frappe.throw(_("El importe neto de la línea {0} no puede ser negativo.").format(line_code))
		economic_category = _ensure_link(
			"NXR Economic Category", line.get("economic_category"), "clasificación económica", required=False
		)
		prepared.append(
			{
				"line_code": line_code,
				"item_type": item_type,
				"catalog_item": catalog_item,
				"description": description,
				"quantity": str(quantity),
				"uom": uom,
				"unit_rate": str(unit_rate),
				"amount": str(amount),
				"charge_amount": str(charge_amount),
				"tax_rate": str(tax_rate),
				"tax_amount": str(tax_amount),
				"discount_rate": str(discount_rate),
				"discount_amount": str(discount_amount),
				"net_amount": str(net_amount),
				"economic_category": economic_category,
				"delivery_date": line.get("delivery_date"),
				"tolerance_percentage": str(money(line.get("tolerance_percentage", 10))),
				"notes": line.get("notes"),
			}
		)
	try:
		order_line_amounts(prepared)
	except PurchaseValidationError as exc:
		frappe.throw(_(str(exc)))
	return prepared


def _snapshot(doc: Any) -> dict[str, Any]:
	return {
		"name": doc.name,
		"document_number": doc.document_number,
		"status": doc.status,
		"purchase_request": doc.purchase_request,
		"supplier_quotation": doc.supplier_quotation,
		"supplier_profile": doc.supplier_profile,
		"supplier_entity": doc.supplier_entity,
		"project": doc.project,
		"cost_center": doc.cost_center,
		"currency": doc.currency,
		"order_date": doc.order_date,
		"delivery_date": doc.delivery_date,
		"payment_terms": doc.payment_terms,
		"delivery_terms": doc.delivery_terms,
		"warranty": doc.warranty,
		"notes": doc.notes,
		"total_amount": doc.total_amount,
		"fund_source": doc.fund_source,
		"lines": [
			{
				"name": line.name,
				"line_code": line.line_code,
				"item_type": line.item_type,
				"catalog_item": line.catalog_item,
				"description": line.description,
				"quantity": line.quantity,
				"uom": line.uom,
				"unit_rate": line.unit_rate,
				"amount": line.amount,
				"charge_amount": line.charge_amount,
				"tax_rate": line.tax_rate,
				"tax_amount": line.tax_amount,
				"discount_rate": line.discount_rate,
				"discount_amount": line.discount_amount,
				"net_amount": line.net_amount,
				"economic_category": line.economic_category,
				"delivery_date": line.delivery_date,
				"tolerance_percentage": line.tolerance_percentage,
			}
			for line in doc.lines
		],
	}


def _total_from_lines(prepared: list[dict[str, Any]]) -> str:
	return str(sum(money(line["net_amount"]) for line in prepared))


@frappe.whitelist(methods=["POST"])
def create_order(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("create_purchase_order")
	data = parse_payload(payload)
	purchase_request = _ensure_link(
		"NXR Purchase Request", data.get("purchase_request"), "solicitud de compra"
	)
	pr_status = frappe.db.get_value("NXR Purchase Request", purchase_request, "status")
	if pr_status != "Approved":
		frappe.throw(_("Solo solicitudes aprobadas pueden generar órdenes de compra."))
	supplier_quotation = _ensure_link(
		"NXR Supplier Quotation", data.get("supplier_quotation"), "cotización de proveedor"
	)
	q_selected = frappe.db.get_value("NXR Supplier Quotation", supplier_quotation, "selected")
	if not q_selected:
		frappe.throw(_("Solo cotizaciones seleccionadas pueden convertirse en órdenes."))
	supplier_profile = _ensure_link(
		"NXR Supplier Profile", data.get("supplier_profile"), "perfil de proveedor"
	)
	supplier_entity = _resolve_supplier(supplier_profile)
	pr_doc = frappe.get_doc("NXR Purchase Request", purchase_request)
	q_doc = frappe.get_doc("NXR Supplier Quotation", supplier_quotation)
	currency = _ensure_link("Currency", data.get("currency") or pr_doc.currency, "moneda")
	lines = _normalized_lines(list(data.get("lines") or [row.as_dict() for row in q_doc.lines]))
	total = _total_from_lines(lines)
	fund_source = _ensure_link(
		"NXR Fund Source", data.get("fund_source") or pr_doc.fund_source, "fuente de fondos", required=False
	)
	key = _required(data, "idempotency_key", "La orden requiere clave de idempotencia.")
	normalized = {**data, "supplier_entity": supplier_entity, "lines": lines, "total_amount": total}
	fingerprint = canonical_payload_hash(normalized)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		number, sequence = issue_document_number("NXR Purchase Order", key)
		with service_write():
			doc = frappe.get_doc(
				{
					"doctype": "NXR Purchase Order",
					"document_number": number,
					"status": "Draft",
					"purchase_request": purchase_request,
					"supplier_quotation": supplier_quotation,
					"supplier_profile": supplier_profile,
					"supplier_entity": supplier_entity,
					"project": pr_doc.project,
					"cost_center": pr_doc.cost_center,
					"currency": currency,
					"order_date": data.get("order_date") or frappe.utils.getdate(),
					"delivery_date": data.get("delivery_date") or q_doc.valid_until,
					"payment_terms": data.get("payment_terms") or q_doc.payment_terms,
					"delivery_terms": data.get("delivery_terms") or q_doc.delivery_terms,
					"warranty": data.get("warranty") or q_doc.warranty,
					"notes": data.get("notes"),
					"total_amount": total,
					"fund_source": fund_source,
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
		audit("purchase_order_created", "NXR Purchase Order", doc.name, fingerprint, correlation_id, result)
		complete_idempotency(idem, "NXR Purchase Order", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def transition_order(
	order: str, status: str, idempotency_key: str, reason: str | None = None
) -> dict[str, Any]:
	target = str(status or "").strip().title()
	if target == "Confirmed":
		require_action("submit_purchase_order")
	else:
		require_action("approve_purchase_order")
	payload = {"order": order, "status": target, "reason": str(reason or "").strip()}
	fingerprint = canonical_payload_hash(payload)
	correlation_id = correlation(payload)
	point = savepoint()
	try:
		idem, cached = start_idempotency(idempotency_key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		doc = _lock(order)
		try:
			assert_order_transition(str(doc.status), target)
		except PurchaseValidationError as exc:
			frappe.throw(_(str(exc)))
		if target in {"Cancelled"} and not payload["reason"]:
			frappe.throw(_("La cancelación requiere motivo."))
		with service_write():
			doc.status = target
			if target == "Confirmed":
				doc.confirmed_by = frappe.session.user
				doc.confirmed_at = now_datetime()
			if target == "Approved":
				doc.approved_by = frappe.session.user
				doc.approved_at = now_datetime()
			if target == "Sent":
				doc.sent_by = frappe.session.user
				doc.sent_at = now_datetime()
			doc.save(ignore_permissions=True)
		result = _snapshot(doc)
		audit(
			"purchase_order_transitioned", "NXR Purchase Order", doc.name, fingerprint, correlation_id, result
		)
		complete_idempotency(idem, "NXR Purchase Order", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["GET"])
def get_order(order: str) -> dict[str, Any]:
	# NXR-SEC-0001 (Bloque 19): permiso contra el proyecto real del documento, no
	# uno declarado por el cliente.
	doc = frappe.get_doc("NXR Purchase Order", order)
	require_project_access(doc.project, action="read_purchases")
	return _snapshot(doc)


@frappe.whitelist(methods=["GET"])
def list_orders(
	project: str | None = None, status: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
	require_project_access(project, action="read_purchases")
	filters: dict[str, Any] = {}
	if project:
		filters["project"] = project
	if status:
		filters["status"] = status
	rows = frappe.get_all(
		"NXR Purchase Order",
		filters=filters,
		fields=["name"],
		order_by="modified desc",
		limit=min(max(int(limit or 100), 1), 500),
	)
	return [_snapshot(frappe.get_doc("NXR Purchase Order", row.name)) for row in rows]
