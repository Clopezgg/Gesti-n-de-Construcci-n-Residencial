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
from nexora.quality.core import assert_transition, assert_valid_result

#: NXR-CAL-0001 (Bloque 26): `NXR Quality Check` existe desde el Bloque 13 con su
#: propio controlador (`before_insert`/`before_save` exige `require_service_write()`,
#: mismo bloqueo que cualquier otro doctype financiero sensible) pero nunca tuvo un
#: punto de entrada real — sin este módulo, ni siquiera un Administrador podía crear
#: o transicionar un control de calidad desde afuera del propio doctype. Mismo
#: patrón exacto que `progress/service.py` (Bloque 25), que resolvió el mismo
#: problema para `NXR Progress Record`.


@frappe.whitelist(methods=["POST"])
def create_quality_check(payload: str | Mapping[str, Any]) -> dict[str, Any]:
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
		if not data.get("project"):
			frappe.throw(_("El proyecto es obligatorio."))
		if not data.get("description"):
			frappe.throw(_("La descripción es obligatoria."))
		if not data.get("checked_by"):
			frappe.throw(_("Debe indicar quién realizó el control."))
		if not data.get("check_date"):
			frappe.throw(_("La fecha del control es obligatoria."))
		result_value = assert_valid_result(data.get("result"))
		number, sequence = issue_document_number("NXR Quality Check", data["idempotency_key"])
		with service_write():
			record = frappe.get_doc(
				{
					"doctype": "NXR Quality Check",
					"document_number": number,
					"status": "Open",
					"project": data["project"],
					"phase": data.get("phase"),
					"progress_record": data.get("progress_record"),
					"description": data["description"],
					"result": result_value,
					"observations": data.get("observations"),
					"checked_by": data["checked_by"],
					"check_date": data["check_date"],
					"corrective_actions": data.get("corrective_actions"),
					"idempotency_key": data["idempotency_key"],
					"payload_hash": fingerprint,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
		link_sequence(sequence, record.name)
		result = {"name": record.name, "document_number": number, "status": "Open"}
		audit("quality_check_created", "NXR Quality Check", record.name, fingerprint, correlation_id, result)
		complete_idempotency(idem, "NXR Quality Check", record.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def transition_quality_check(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("approve")
	record_name = data["record"]
	record = frappe.get_doc("NXR Quality Check", record_name)
	frappe.db.sql("SELECT name FROM `tabNXR Quality Check` WHERE name=%s FOR UPDATE", record_name)
	target = str(data.get("target_status") or "")
	assert_transition(record.status, target)
	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		with service_write():
			record.status = target
			if data.get("result"):
				record.result = assert_valid_result(data.get("result"))
			if data.get("corrective_actions"):
				record.corrective_actions = data["corrective_actions"]
			record.save(ignore_permissions=True)
		result = {"name": record.name, "document_number": record.document_number, "status": target}
		audit(
			"quality_check_transitioned",
			"NXR Quality Check",
			record.name,
			fingerprint,
			correlation_id,
			result,
		)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def list_quality_checks(payload: str | Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
	"""Mismo alcance por proyecto que `progress.service.list_progress_records`
	— regresión directa de NXR-SEC-0001 si se relaja."""
	data = parse_payload(payload or {})
	project = str(data.get("project") or "").strip() or None
	require_project_access(project, action="preview")
	filters = {"project": project} if project else {}
	if data.get("status"):
		filters["status"] = data["status"]
	if data.get("progress_record"):
		filters["progress_record"] = data["progress_record"]
	return frappe.get_all(
		"NXR Quality Check",
		filters=filters,
		fields=[
			"name",
			"document_number",
			"status",
			"project",
			"phase",
			"progress_record",
			"description",
			"result",
			"observations",
			"checked_by",
			"check_date",
			"corrective_actions",
		],
		order_by="check_date desc, creation desc",
		limit_page_length=min(max(int(data.get("limit") or 50), 1), 200),
	)
