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
from nexora.purchases.quotation_core import (
	assert_quotation_transition,
)
from nexora.purchases.request_core import PurchaseValidationError, money


def _required(data: Mapping[str, Any], fieldname: str, message: str) -> str:
	value = str(data.get(fieldname) or "").strip()
	if not value:
		frappe.throw(_(message))
	return value


def _lock(name: str) -> Any:
	table = frappe.qb.DocType("NXR Supplier Quotation")
	rows = (frappe.qb.from_(table).select(table.name).where(table.name == name).for_update()).run()
	if not rows:
		frappe.throw(_("La cotización no existe."))
	return frappe.get_doc("NXR Supplier Quotation", name)


def _ensure_link(doctype: str, name: str | None, label: str, *, required: bool = True) -> str | None:
	value = str(name or "").strip()
	if not value:
		if required:
			frappe.throw(_("La cotización requiere {0}.").format(label))
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
		if item_type not in {"Goods", "Service"}:
			frappe.throw(_("El tipo de línea debe ser Goods o Service."))
		catalog_item = _ensure_link("Item", line.get("catalog_item"), "artículo de catálogo", required=False)
		uom = _ensure_link("UOM", line.get("uom"), "unidad de medida")
		description = _required(line, "description", "Cada línea requiere descripción.")
		quantity = money(line.get("quantity"))
		if money(line.get("quantity")) <= 0:
			frappe.throw(_("La línea {0} requiere cantidad positiva.").format(line_code))
		unit_rate = money(line.get("unit_rate"))
		if unit_rate < 0:
			frappe.throw(_("La línea {0} no admite precio negativo.").format(line_code))
		amount = money(quantity * unit_rate)
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
				"economic_category": _ensure_link(
					"NXR Economic Category",
					line.get("economic_category"),
					"clasificación económica",
					required=False,
				),
				"delivery_date": line.get("delivery_date"),
				"notes": line.get("notes"),
			}
		)
	return prepared


def _snapshot(doc: Any) -> dict[str, Any]:
	return {
		"quotation": doc.name,
		"document_number": doc.document_number,
		"status": doc.status,
		"purchase_request": doc.purchase_request,
		"supplier_profile": doc.supplier_profile,
		"supplier_entity": doc.supplier_entity,
		"project": doc.project,
		"cost_center": doc.cost_center,
		"currency": doc.currency,
		"quotation_date": doc.quotation_date,
		"valid_until": doc.valid_until,
		"payment_terms": doc.payment_terms,
		"warranty": doc.warranty,
		"delivery_terms": doc.delivery_terms,
		"total_amount": doc.total_amount,
		"notes": doc.notes,
		"evidence": doc.evidence,
		"selected": int(doc.selected or 0),
		"selection_reason": doc.selection_reason,
		"selected_at": doc.selected_at,
		"selected_by": doc.selected_by,
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
				"economic_category": line.economic_category,
				"delivery_date": line.delivery_date,
			}
			for line in doc.lines
		],
	}


@frappe.whitelist(methods=["POST"])
def create_quotation(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("create_purchase_request")
	data = parse_payload(payload)
	purchase_request = _ensure_link(
		"NXR Purchase Request", data.get("purchase_request"), "solicitud de compra"
	)
	supplier_profile = _ensure_link(
		"NXR Supplier Profile", data.get("supplier_profile"), "perfil de proveedor"
	)
	supplier_entity = _resolve_supplier(supplier_profile)
	pr_doc = frappe.get_doc("NXR Purchase Request", purchase_request)
	currency = _ensure_link("Currency", data.get("currency") or pr_doc.currency, "moneda")
	valid_until = _required(data, "valid_until", "La cotización requiere fecha de vencimiento.")
	lines = _normalized_lines(list(data.get("lines") or []))
	key = _required(data, "idempotency_key", "La cotización requiere clave de idempotencia.")
	normalized = {**data, "supplier_entity": supplier_entity, "lines": lines}
	fingerprint = canonical_payload_hash(normalized)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		number, sequence = issue_document_number("NXR Supplier Quotation", key)
		with service_write():
			doc = frappe.get_doc(
				{
					"doctype": "NXR Supplier Quotation",
					"document_number": number,
					"status": "Draft",
					"purchase_request": purchase_request,
					"supplier_profile": supplier_profile,
					"supplier_entity": supplier_entity,
					"project": pr_doc.project,
					"cost_center": pr_doc.cost_center,
					"currency": currency,
					"quotation_date": data.get("quotation_date") or frappe.utils.getdate(),
					"valid_until": valid_until,
					"payment_terms": data.get("payment_terms"),
					"warranty": data.get("warranty"),
					"delivery_terms": data.get("delivery_terms"),
					"evidence": _ensure_link(
						"NXR Evidence", data.get("evidence"), "evidencia", required=False
					),
					"notes": data.get("notes"),
					"lines": lines,
					"idempotency_key": key,
					"payload_hash": fingerprint,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
		link_sequence(sequence, doc.name)
		result = _snapshot(doc)
		audit(
			"supplier_quotation_created",
			"NXR Supplier Quotation",
			doc.name,
			fingerprint,
			correlation_id,
			result,
		)
		complete_idempotency(idem, "NXR Supplier Quotation", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def transition_quotation(
	quotation: str, status: str, idempotency_key: str, reason: str | None = None
) -> dict[str, Any]:
	target = str(status or "").strip().title()
	if target in {"Submitted"}:
		require_action("submit_purchase_request")
	else:
		require_action("approve_purchase_request")
	payload = {"quotation": quotation, "status": target, "reason": str(reason or "").strip()}
	fingerprint = canonical_payload_hash(payload)
	correlation_id = correlation(payload)
	point = savepoint()
	try:
		idem, cached = start_idempotency(idempotency_key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		doc = _lock(quotation)
		try:
			assert_quotation_transition(str(doc.status), target)
		except PurchaseValidationError as exc:
			frappe.throw(_(str(exc)))
		if target in {"Rejected", "Cancelled"} and not payload["reason"]:
			frappe.throw(_("El rechazo o cancelación requiere motivo."))
		if target == "Accepted" and not payload["reason"]:
			frappe.throw(_("La aceptación de cotización requiere motivo de selección."))
		with service_write():
			doc.status = target
			if target == "Accepted":
				doc.selected = 1
				doc.selection_reason = payload["reason"]
				doc.selected_at = now_datetime()
				doc.selected_by = frappe.session.user
				_deselect_other_quotations(doc.purchase_request, doc.name)
			doc.save(ignore_permissions=True)
		result = _snapshot(doc)
		audit(
			"supplier_quotation_transitioned",
			"NXR Supplier Quotation",
			doc.name,
			fingerprint,
			correlation_id,
			result,
		)
		complete_idempotency(idem, "NXR Supplier Quotation", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


def _deselect_other_quotations(purchase_request: str, exclude: str) -> None:
	others = frappe.get_all(
		"NXR Supplier Quotation",
		filters={"purchase_request": purchase_request, "selected": 1, "name": ["!=", exclude]},
	)
	for row in others:
		other = frappe.get_doc("NXR Supplier Quotation", row.name)
		other.selected = 0
		other.selection_reason = ""
		other.selected_at = None
		other.selected_by = None
		with service_write():
			other.save(ignore_permissions=True)
		audit(
			"supplier_quotation_deselected",
			"NXR Supplier Quotation",
			other.name,
			"",
			"",
			{"deselected": True},
		)


@frappe.whitelist(methods=["GET"])
def get_quotation(quotation: str) -> dict[str, Any]:
	# El permiso se comprueba contra el proyecto real del documento, no contra uno
	# declarado por el cliente (NXR-SEC-0001, Bloque 19): un "NEXORA Project Viewer"
	# restringido a un proyecto no puede leer una cotización de otro solo porque
	# adivine o enumere su ID.
	doc = frappe.get_doc("NXR Supplier Quotation", quotation)
	require_project_access(doc.project, action="read_purchases")
	return _snapshot(doc)


@frappe.whitelist(methods=["GET"])
def list_quotations(
	purchase_request: str | None = None,
	supplier_profile: str | None = None,
	status: str | None = None,
	limit: int = 100,
) -> list[dict[str, Any]]:
	if purchase_request:
		project = frappe.db.get_value("NXR Purchase Request", purchase_request, "project")
		require_project_access(project, action="read_purchases")
	else:
		# Sin `purchase_request`, la lista puede abarcar varios proyectos: solo un
		# rol con `view_all_projects` puede pedirla sin acotar.
		require_project_access(None, action="read_purchases")
	filters: dict[str, Any] = {}
	if purchase_request:
		filters["purchase_request"] = purchase_request
	if supplier_profile:
		filters["supplier_profile"] = supplier_profile
	if status:
		filters["status"] = status
	rows = frappe.get_all(
		"NXR Supplier Quotation",
		filters=filters,
		fields=["name"],
		order_by="modified desc",
		limit=min(max(int(limit or 100), 1), 500),
	)
	return [_snapshot(frappe.get_doc("NXR Supplier Quotation", row.name)) for row in rows]


@frappe.whitelist(methods=["GET"])
def compare_quotations(purchase_request: str) -> list[dict[str, Any]]:
	project = frappe.db.get_value("NXR Purchase Request", purchase_request, "project")
	require_project_access(project, action="read_purchases")
	rows = frappe.get_all(
		"NXR Supplier Quotation",
		filters={"purchase_request": purchase_request, "status": ["in", ["Submitted", "Accepted"]]},
		fields=["name"],
		order_by="total_amount asc",
	)
	return [_snapshot(frappe.get_doc("NXR Supplier Quotation", row.name)) for row in rows]
