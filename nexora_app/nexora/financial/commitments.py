from __future__ import annotations

from typing import Any, Mapping

import frappe
from frappe import _

from nexora.financial.context import service_write
from nexora.financial.core import canonical_payload_hash, money
from nexora.financial.db import (
    audit, commitment_outstanding, complete_idempotency, correlation, issue_document_number,
    link_sequence, operation_doc, parse_payload, persist_effects, preview, rollback, savepoint, start_idempotency,
)
from nexora.financial.operations import execute
from nexora.permissions import require_action


@frappe.whitelist(methods=["POST"])
def create_commitment(payload: str | Mapping[str, Any]) -> dict[str, Any]:
    data = parse_payload(payload)
    data.update({"operation_type": "Commitment Reserve", "idempotency_key": str(data.get("idempotency_key") or "")})
    require_action("approve")
    fingerprint = canonical_payload_hash(data)
    correlation_id = correlation(data)
    point = savepoint()
    try:
        idem, cached = start_idempotency(data["idempotency_key"], fingerprint, correlation_id)
        if cached is not None:
            return cached
        preview_data = preview(data, lock=True)
        if data.get("preview_hash") and data["preview_hash"] != preview_data["preview_hash"]:
            frappe.throw(_("La vista previa cambió; revísela nuevamente antes de crear el compromiso."))
        commitment_number, commitment_sequence = issue_document_number("NXR Commitment", data["idempotency_key"])
        with service_write():
            commitment = frappe.get_doc(
                {
                    "doctype": "NXR Commitment", "document_number": commitment_number, "status": "Approved",
                    "project": data["project"], "commitment_date": data.get("operation_date") or frappe.utils.today(),
                    "expiry_date": data.get("expiry_date"), "amount_hnl": data["amount_hnl"],
                    "beneficiary_doctype": data.get("beneficiary_doctype"), "beneficiary": data.get("beneficiary"),
                    "cost_center": data.get("cost_center"), "economic_category": data.get("economic_category"),
                    "description": data.get("description") or "Compromiso NEXORA", "requester": data.get("requester"),
                    "approved_by": data.get("approved_by"), "idempotency_key": data["idempotency_key"],
                    "payload_hash": fingerprint, "evidence": data.get("evidence"), "correlation_id": correlation_id,
                }
            ).insert(ignore_permissions=True)
        link_sequence(commitment_sequence, commitment.name)
        operation_number, operation_sequence = issue_document_number("NXR Operation", data["idempotency_key"])
        operation = operation_doc(data, operation_number, fingerprint, preview_data, correlation_id, commitment.name)
        persist_effects(operation, preview_data, correlation_id, commitment.name)
        link_sequence(operation_sequence, operation.name)
        result = {"commitment": commitment.name, "commitment_number": commitment_number, "operation": operation.name, "document_number": operation_number, "sources": preview_data["sources"]}
        audit("commitment_created", "NXR Commitment", commitment.name, fingerprint, correlation_id, result)
        complete_idempotency(idem, "NXR Commitment", commitment.name, result)
        return result
    except Exception:
        rollback(point)
        raise


def _change(payload: str | Mapping[str, Any], operation_type: str, action: str) -> dict[str, Any]:
    data = parse_payload(payload)
    commitment = frappe.get_doc("NXR Commitment", data["commitment"])
    frappe.db.sql("SELECT name FROM `tabNXR Commitment` WHERE name=%s FOR UPDATE", commitment.name)
    data.update({"operation_type": operation_type, "project": commitment.project})
    if money(data["amount_hnl"]) > commitment_outstanding(commitment.name):
        frappe.throw(_("El importe supera el saldo reservado del compromiso."))
    result = execute(data, action=action, commitment=commitment.name)
    outstanding = commitment_outstanding(commitment.name)
    if operation_type == "Commitment Execution":
        commitment.status = "Executed" if outstanding == 0 else "Partially Executed"
    else:
        commitment.status = "Released" if outstanding == 0 else "Partially Released"
    with service_write():
        commitment.save(ignore_permissions=True)
    return result


@frappe.whitelist(methods=["POST"])
def execute_commitment(payload: str | Mapping[str, Any]) -> dict[str, Any]:
    return _change(payload, "Commitment Execution", "execute")


@frappe.whitelist(methods=["POST"])
def release_commitment(payload: str | Mapping[str, Any]) -> dict[str, Any]:
    return _change(payload, "Commitment Release", "approve")
