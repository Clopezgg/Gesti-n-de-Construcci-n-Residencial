from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.financial.commitments import create_commitment, execute_commitment, release_commitment
from nexora.financial.context import service_write
from nexora.financial.core import canonical_payload_hash, money
from nexora.financial.db import (
	audit,
	commitment_outstanding,
	completed_idempotent_response,
	correlation,
	parse_payload,
)
from nexora.permissions import require_action, require_project_access

PO_APPROVED = "Approved"
PO_CANCELLED = "Cancelled"


def _commitment_name(order: Any) -> str | None:
	return str(getattr(order, "financial_commitment", "") or "").strip() or None


def _ensure_source(order: Any) -> str:
	source = str(getattr(order, "fund_source", "") or "").strip()
	if not source:
		frappe.throw(_("La orden de compra requiere una fuente de fondos antes de aprobarse."))
	if not frappe.db.exists("NXR Fund Source", source):
		frappe.throw(_("La fuente de fondos de la orden de compra no existe."))
	return source


def _commitment_payload(order: Any) -> dict[str, Any]:
	source = _ensure_source(order)
	return {
		"idempotency_key": f"purchase-order-commitment:{order.name}",
		"project": order.project,
		"amount_hnl": money(order.total_amount),
		"allocations": [{"source": source, "amount_hnl": money(order.total_amount)}],
		"cost_center": order.cost_center,
		"economic_category": _first_economic_category(order),
		"requester": order.confirmed_by or frappe.session.user,
		"approved_by": order.approved_by or frappe.session.user,
		"operation_date": order.order_date,
		"description": f"Reserva financiera de orden de compra {order.document_number}",
		"beneficiary_doctype": "NXR Entity",
		"beneficiary": order.supplier_entity,
		"reference_doctype": "NXR Purchase Order",
		"reference_name": order.name,
		"evidence": order.evidence,
	}


def _first_economic_category(order: Any) -> str | None:
	for line in getattr(order, "lines", []) or []:
		value = str(getattr(line, "economic_category", "") or "").strip()
		if value:
			return value
	return None


def _attach_commitment(order: Any, commitment_name: str) -> None:
	order.flags.in_purchase_financial_bridge = True
	commitment = frappe.get_doc("NXR Commitment", commitment_name)
	with service_write():
		commitment.reference_doctype = "NXR Purchase Order"
		commitment.reference_name = order.name
		commitment.save(ignore_permissions=True)
		order.financial_commitment = commitment.name
		order.commitment_reserved_hnl = money(commitment.amount_hnl)
		order.commitment_executed_hnl = 0
		order.save(ignore_permissions=True)


def _reserve_order(order: Any) -> None:
	if order.status != PO_APPROVED or _commitment_name(order):
		return
	result = create_commitment(_commitment_payload(order))
	commitment_name = str(result.get("commitment") or "").strip()
	if not commitment_name:
		frappe.throw(_("No se pudo crear el compromiso financiero de la orden de compra."))
	_attach_commitment(order, commitment_name)
	audit(
		"purchase_order_commitment_reserved",
		"NXR Purchase Order",
		order.name,
		canonical_payload_hash(_commitment_payload(order)),
		correlation({"purchase_order": order.name}),
		{"commitment": commitment_name, "amount_hnl": str(order.total_amount)},
	)


def _release_order(order: Any) -> None:
	commitment_name = _commitment_name(order)
	if order.status != PO_CANCELLED or not commitment_name:
		return
	commitment = frappe.get_doc("NXR Commitment", commitment_name)
	outstanding = money(commitment_outstanding(commitment.name))
	if outstanding <= 0 or commitment.status in {"Released", "Executed", "Cancelled"}:
		return
	source = _ensure_source(order)
	release_commitment(
		{
			"idempotency_key": f"purchase-order-release:{order.name}:{commitment.name}",
			"commitment": commitment.name,
			"amount_hnl": outstanding,
			"allocations": [{"source": source, "amount_hnl": outstanding}],
			"project": order.project,
			"requester": frappe.session.user,
			"approved_by": frappe.session.user,
			"reference_doctype": "NXR Purchase Order",
			"reference_name": order.name,
			"description": f"Liberación por cancelación de orden de compra {order.document_number}",
		}
	)


def sync_purchase_order_financials(doc: Any, method: str | None = None) -> None:
	"""Synchronize PO lifecycle with the canonical commitment ledger."""
	if getattr(doc.flags, "in_purchase_financial_bridge", False):
		return
	if doc.status == PO_APPROVED:
		_reserve_order(doc)
	elif doc.status == PO_CANCELLED:
		_release_order(doc)


def _received_amount(order_name: str) -> Any:
	rows = frappe.db.sql(
		"""
		SELECT SUM(COALESCE(line.accepted_quantity, 0) * COALESCE(line.unit_rate, 0)) AS amount
		FROM `tabNXR Goods Receipt Line` line
		INNER JOIN `tabNXR Goods Receipt` receipt ON receipt.name = line.parent
		WHERE receipt.purchase_order = %s AND receipt.status = 'Completed'
		""",
		order_name,
		as_dict=True,
	)
	return money(rows[0].amount if rows else 0)


@frappe.whitelist(methods=["POST"])
def pay_purchase_order(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Execute a purchase payment through the canonical commitment/ledger engine."""
	data = parse_payload(payload)
	order_name = str(data.get("purchase_order") or "").strip()
	key = str(data.get("idempotency_key") or "").strip()
	if not order_name:
		frappe.throw(_("Seleccione la orden de compra."))
	if not key:
		frappe.throw(_("El pago de compra requiere una clave de idempotencia."))
	order = frappe.get_doc("NXR Purchase Order", order_name)
	require_project_access(order.project, action="execute")
	require_action("execute")
	if order.status not in {"Sent", "Completed"}:
		frappe.throw(_("La orden de compra debe estar enviada o completada antes del pago."))
	commitment_name = _commitment_name(order)
	if not commitment_name:
		frappe.throw(_("La orden de compra no tiene compromiso financiero asociado."))
	# Un reintento de un pago ya ejecutado no puede exigir que el compromiso
	# siga teniendo saldo: la propia ejecución ya lo consumió, así que
	# revalidar "recibido"/"saldo disponible" aquí convertía cada reintento
	# legítimo —doble clic, corte de red— en un rechazo de negocio en vez de
	# devolver la respuesta que `execute()` ya sabe reconocer por su propia
	# clave de idempotencia (mismo patrón que `execute_operational_movement`).
	replay = completed_idempotent_response(key)
	if replay is not None:
		return {
			"purchase_order": order.name,
			"commitment": commitment_name,
			"received_hnl": str(_received_amount(order.name)),
			"executed_hnl": str(money(data.get("amount_hnl"))),
			"commitment_outstanding_hnl": str(money(commitment_outstanding(commitment_name))),
			**replay,
		}
	source = _ensure_source(order)
	amount = money(data.get("amount_hnl"))
	if amount <= 0:
		frappe.throw(_("El pago debe ser mayor que cero."))
	received = _received_amount(order.name)
	outstanding = money(commitment_outstanding(commitment_name))
	if amount > received:
		frappe.throw(_("El pago no puede superar el importe recibido y aceptado."))
	if amount > outstanding:
		frappe.throw(_("El pago supera el saldo disponible del compromiso de la orden."))
	category = str(data.get("economic_category") or _first_economic_category(order) or "").strip()
	if not category:
		frappe.throw(_("El pago requiere clasificación económica."))
	result = execute_commitment(
		{
			"idempotency_key": key,
			"commitment": commitment_name,
			"amount_hnl": amount,
			"allocations": [{"source": source, "amount_hnl": amount}],
			"project": order.project,
			"cost_center": order.cost_center,
			"economic_category": category,
			"requester": data.get("requester") or frappe.session.user,
			"approved_by": data.get("approved_by") or frappe.session.user,
			"reference_doctype": "NXR Purchase Order",
			"reference_name": order.name,
			"description": str(data.get("description") or f"Pago de orden de compra {order.document_number}"),
			"operation_date": data.get("operation_date") or frappe.utils.today(),
			"beneficiary_doctype": "NXR Entity",
			"beneficiary": order.supplier_entity,
			"evidence": data.get("evidence") or order.evidence,
		}
	)
	order.flags.in_purchase_financial_bridge = True
	with service_write():
		order.commitment_executed_hnl = money(order.commitment_executed_hnl) + amount
		order.save(ignore_permissions=True)
	return {
		"purchase_order": order.name,
		"commitment": commitment_name,
		"received_hnl": str(received),
		"executed_hnl": str(amount),
		"commitment_outstanding_hnl": str(money(commitment_outstanding(commitment_name))),
		**result,
	}
