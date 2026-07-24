from __future__ import annotations

from typing import Any, Mapping

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
from nexora.permissions import require_action
from nexora.purchases.request_core import (
	PURCHASE_ITEM_TYPES,
	PURCHASE_PRIORITIES,
	PurchaseValidationError,
	assert_request_transition,
	money,
	request_line_amounts,
	validate_request_dates,
)


def _required(data: Mapping[str, Any], fieldname: str, message: str) -> str:
	value = str(data.get(fieldname) or "").strip()
	if not value:
		frappe.throw(_(message))
	return value


def _lock(name: str) -> Any:
	table = frappe.qb.DocType("NXR Purchase Request")
	rows = (frappe.qb.from_(table).select(table.name).where(table.name == name).for_update()).run()
	if not rows:
		frappe.throw(_("La solicitud de compra no existe."))
	return frappe.get_doc("NXR Purchase Request", name)


def _ensure_link(doctype: str, name: str | None, label: str, *, required: bool = True) -> str | None:
	value = str(name or "").strip()
	if not value:
		if required:
			frappe.throw(_("La solicitud requiere {0}.").format(label))
		return None
	if not frappe.db.exists(doctype, value):
		frappe.throw(_("El valor de {0} no existe.").format(label))
	return value


def _normalized_lines(
	lines: list[Mapping[str, Any]], parent_cost_center: str, parent_required_by: str
) -> tuple[list[dict[str, Any]], Any]:
	prepared: list[dict[str, Any]] = []
	for index, raw in enumerate(lines, start=1):
		line = dict(raw)
		line_code = str(line.get("line_code") or f"{index:03d}").strip()
		item_type = str(line.get("item_type") or "Goods").strip().title()
		if item_type not in PURCHASE_ITEM_TYPES:
			frappe.throw(_("El tipo de línea debe ser Goods o Service."))
		catalog_item = _ensure_link("Item", line.get("catalog_item"), "artículo de catálogo", required=False)
		if catalog_item and frappe.db.get_value("Item", catalog_item, "disabled"):
			frappe.throw(_("El artículo de catálogo está deshabilitado."))
		uom = _ensure_link("UOM", line.get("uom"), "unidad de medida")
		economic_category = _ensure_link(
			"NXR Economic Category", line.get("economic_category"), "clasificación económica"
		)
		if not frappe.db.get_value("NXR Economic Category", economic_category, "active"):
			frappe.throw(_("La clasificación económica de la línea está inactiva."))
		cost_center = _ensure_link(
			"Cost Center", line.get("cost_center") or parent_cost_center, "centro de costo"
		)
		quantity = money(line.get("quantity"))
		unit_rate = money(line.get("estimated_unit_rate"))
		amount = money(quantity * unit_rate)
		prepared.append(
			{
				"line_code": line_code,
				"item_type": item_type,
				"catalog_item": catalog_item,
				"description": _required(line, "description", "Cada línea requiere descripción."),
				"quantity": str(quantity),
				"uom": uom,
				"estimated_unit_rate": str(unit_rate),
				"estimated_amount": str(amount),
				"economic_category": economic_category,
				"cost_center": cost_center,
				"required_by": line.get("required_by") or parent_required_by,
				"notes": line.get("notes"),
			}
		)
	try:
		amounts = request_line_amounts(prepared)
	except PurchaseValidationError as exc:
		frappe.throw(_(str(exc)))
	return prepared, amounts


def _snapshot(doc: Any) -> dict[str, Any]:
	return {
		"request": doc.name,
		"document_number": doc.document_number,
		"status": doc.status,
		"request_date": doc.request_date,
		"required_by": doc.required_by,
		"project": doc.project,
		"cost_center": doc.cost_center,
		"fund_source": doc.fund_source,
		"requested_by": doc.requested_by,
		"responsible": doc.responsible,
		"priority": doc.priority,
		"currency": doc.currency,
		"justification": doc.justification,
		"total_amount": doc.total_amount,
		"evidence": doc.evidence,
		"submitted_by": doc.submitted_by,
		"submitted_at": doc.submitted_at,
		"decided_by": doc.decided_by,
		"decided_at": doc.decided_at,
		"decision_reason": doc.decision_reason,
		"lines": [
			{
				"name": line.name,
				"line_code": line.line_code,
				"item_type": line.item_type,
				"catalog_item": line.catalog_item,
				"description": line.description,
				"quantity": line.quantity,
				"uom": line.uom,
				"estimated_unit_rate": line.estimated_unit_rate,
				"estimated_amount": line.estimated_amount,
				"economic_category": line.economic_category,
				"cost_center": line.cost_center,
				"required_by": line.required_by,
			}
			for line in doc.lines
		],
	}


@frappe.whitelist(methods=["POST"])
def create_purchase_request(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("create_purchase_request")
	data = parse_payload(payload)
	request_date = _required(data, "request_date", "La solicitud requiere fecha de solicitud.")
	required_by = _required(data, "required_by", "La solicitud requiere fecha requerida.")
	try:
		validate_request_dates(request_date, required_by)
	except PurchaseValidationError as exc:
		frappe.throw(_(str(exc)))
	project = _ensure_link("Project", data.get("project"), "proyecto")
	cost_center = _ensure_link("Cost Center", data.get("cost_center"), "centro de costo")
	fund_source = _ensure_link(
		"NXR Fund Source", data.get("fund_source"), "fuente prevista", required=False
	)
	responsible = _ensure_link("User", data.get("responsible"), "responsable")
	currency = _ensure_link("Currency", data.get("currency") or "HNL", "moneda")
	evidence = _ensure_link("NXR Evidence", data.get("evidence"), "evidencia", required=False)
	priority = str(data.get("priority") or "Normal").strip().title()
	if priority not in PURCHASE_PRIORITIES:
		frappe.throw(_("La prioridad de compra no está permitida."))
	lines, amounts = _normalized_lines(list(data.get("lines") or []), str(cost_center), required_by)
	key = _required(data, "idempotency_key", "La solicitud requiere clave de idempotencia.")
	normalized = {
		**data,
		"project": project,
		"cost_center": cost_center,
		"fund_source": fund_source,
		"responsible": responsible,
		"currency": currency,
		"evidence": evidence,
		"priority": priority,
		"lines": lines,
		"total_amount": str(amounts.total),
	}
	fingerprint = canonical_payload_hash(normalized)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		number, sequence = issue_document_number("NXR Purchase Request", key)
		with service_write():
			doc = frappe.get_doc(
				{
					"doctype": "NXR Purchase Request",
					"document_number": number,
					"status": "Draft",
					"request_date": request_date,
					"required_by": required_by,
					"project": project,
					"cost_center": cost_center,
					"fund_source": fund_source,
					"requested_by": frappe.session.user,
					"responsible": responsible,
					"priority": priority,
					"currency": currency,
					"justification": _required(data, "justification", "La solicitud requiere justificación."),
					"total_amount": str(amounts.total),
					"lines": lines,
					"evidence": evidence,
					"idempotency_key": key,
					"payload_hash": fingerprint,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
		link_sequence(sequence, doc.name)
		result = _snapshot(doc)
		audit(
			"purchase_request_created",
			"NXR Purchase Request",
			doc.name,
			fingerprint,
			correlation_id,
			result,
		)
		complete_idempotency(idem, "NXR Purchase Request", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def transition_purchase_request(
	request: str, status: str, idempotency_key: str, reason: str | None = None
) -> dict[str, Any]:
	target = str(status or "").strip().title()
	if target in {"Draft", "In Review"}:
		require_action("submit_purchase_request")
	else:
		require_action("approve_purchase_request")
	payload = {"request": request, "status": target, "reason": str(reason or "").strip()}
	fingerprint = canonical_payload_hash(payload)
	correlation_id = correlation(payload)
	point = savepoint()
	try:
		idem, cached = start_idempotency(idempotency_key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		doc = _lock(request)
		try:
			assert_request_transition(str(doc.status), target)
		except PurchaseValidationError as exc:
			frappe.throw(_(str(exc)))
		if target == "Approved" and money(doc.total_amount) <= 0:
			frappe.throw(_("La aprobación requiere un total estimado mayor que cero."))
		if target in {"Rejected", "Cancelled"} and not payload["reason"]:
			frappe.throw(_("El rechazo o cancelación requiere motivo."))
		with service_write():
			doc.status = target
			if target == "In Review":
				doc.submitted_by = frappe.session.user
				doc.submitted_at = now_datetime()
			if target in {"Approved", "Rejected", "Cancelled"}:
				doc.decided_by = frappe.session.user
				doc.decided_at = now_datetime()
				doc.decision_reason = payload["reason"] or None
			doc.save(ignore_permissions=True)
		result = _snapshot(doc)
		audit(
			"purchase_request_transitioned",
			"NXR Purchase Request",
			doc.name,
			fingerprint,
			correlation_id,
			result,
		)
		complete_idempotency(idem, "NXR Purchase Request", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["GET"])
def get_purchase_request(request: str) -> dict[str, Any]:
	require_action("read_purchases")
	return _snapshot(frappe.get_doc("NXR Purchase Request", request))


@frappe.whitelist(methods=["GET"])
def list_purchase_requests(
	project: str | None = None, status: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
	require_action("read_purchases")
	filters: dict[str, Any] = {}
	if project:
		filters["project"] = project
	if status:
		filters["status"] = status
	rows = frappe.get_all(
		"NXR Purchase Request",
		filters=filters,
		fields=["name"],
		order_by="modified desc",
		limit=min(max(int(limit or 100), 1), 500),
	)
	return [_snapshot(frappe.get_doc("NXR Purchase Request", row.name)) for row in rows]
