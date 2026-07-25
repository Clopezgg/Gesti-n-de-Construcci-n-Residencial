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
from nexora.permissions import require_action
from nexora.progress.core import assert_transition, progress_percent


@frappe.whitelist(methods=["POST"])
def create_progress_record(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	data["idempotency_key"] = str(data.get("idempotency_key") or "")
	require_action("approve")
	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(data["idempotency_key"], fingerprint, correlation_id)
		if cached is not None:
			return cached
		if not data.get("description"):
			frappe.throw(_("La descripción es obligatoria."))
		if not data.get("recorded_date"):
			frappe.throw(_("La fecha de registro es obligatoria."))
		if not data.get("project"):
			frappe.throw(_("El proyecto es obligatorio."))
		pct = progress_percent(data.get("progress_percent", 0))
		number, sequence = issue_document_number("NXR Progress Record", data["idempotency_key"])
		with service_write():
			record = frappe.get_doc(
				{
					"doctype": "NXR Progress Record",
					"document_number": number,
					"status": "Draft",
					"project": data["project"],
					"phase": data.get("phase"),
					"description": data["description"],
					"progress_percent": float(pct),
					"recorded_date": data["recorded_date"],
					"responsible": data.get("responsible"),
					"photos": data.get("photos"),
					"notes": data.get("notes"),
					"idempotency_key": data["idempotency_key"],
					"payload_hash": fingerprint,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
		link_sequence(sequence, record.name)
		result = {
			"name": record.name,
			"document_number": number,
			"status": "Draft",
		}
		audit(
			"progress_record_created", "NXR Progress Record", record.name, fingerprint, correlation_id, result
		)
		complete_idempotency(idem, "NXR Progress Record", record.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def transition_progress_record(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("approve")
	record_name = data["record"]
	record = frappe.get_doc("NXR Progress Record", record_name)
	frappe.db.sql("SELECT name FROM `tabNXR Progress Record` WHERE name=%s FOR UPDATE", record_name)
	target = str(data.get("target_status") or "")
	assert_transition(record.status, target)
	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		with service_write():
			record.status = target
			record.save(ignore_permissions=True)
		result = {"name": record.name, "document_number": record.document_number, "status": target}
		audit(
			"progress_record_transitioned",
			"NXR Progress Record",
			record.name,
			fingerprint,
			correlation_id,
			result,
		)
		return result
	except Exception:
		rollback(point)
		raise
