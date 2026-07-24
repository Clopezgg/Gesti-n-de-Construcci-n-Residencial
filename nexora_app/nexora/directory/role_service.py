from __future__ import annotations

from typing import Any, Mapping

import frappe
from frappe import _

from nexora.directory.common import ROLE_TYPES, _lock, _required
from nexora.directory.core import ROLE_TRANSITIONS, assert_transition, periods_overlap, validate_period
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


def assign_entity_role(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("manage_entity_role")
	data = parse_payload(payload)
	entity = _required(data, "entity", "El rol requiere entidad.")
	role_type = _required(data, "role_type", "El rol requiere tipo.").title()
	if role_type not in ROLE_TYPES:
		frappe.throw(_("Tipo de rol no permitido."))
	valid_from = _required(data, "valid_from", "El rol requiere fecha inicial.")
	try:
		validate_period(valid_from, data.get("valid_until"))
	except ValueError as exc:
		frappe.throw(_(str(exc)))
	idempotency_key = _required(data, "idempotency_key", "El rol requiere clave de idempotencia.")
	payload_hash = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(idempotency_key, payload_hash, correlation_id)
		if cached is not None:
			return cached
		entity_doc = _lock("NXR Entity", entity)
		if entity_doc.status not in {"Active", "Blocked"}:
			frappe.throw(_("Solo una entidad activa o bloqueada puede recibir roles."))
		project = str(data.get("project") or "").strip() or None
		existing = frappe.get_all(
			"NXR Entity Role",
			filters={
				"entity": entity,
				"role_type": role_type,
				"project": project or "",
				"status": ["in", ["Proposed", "Active", "Suspended"]],
			},
			fields=["valid_from", "valid_until"],
		)
		if any(
			periods_overlap(valid_from, data.get("valid_until"), row.valid_from, row.valid_until)
			for row in existing
		):
			frappe.throw(_("Ya existe un rol vigente o superpuesto para ese alcance."))
		number, sequence = issue_document_number("NXR Entity Role", idempotency_key)
		with service_write():
			doc = frappe.get_doc(
				{
					"doctype": "NXR Entity Role",
					"document_number": number,
					"status": "Proposed",
					"entity": entity,
					"role_type": role_type,
					"project": project,
					"valid_from": valid_from,
					"valid_until": data.get("valid_until"),
					"notes": data.get("notes"),
					"assigned_by": frappe.session.user,
					"assigned_at": frappe.utils.now_datetime(),
					"idempotency_key": idempotency_key,
					"payload_hash": payload_hash,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
		link_sequence(sequence, doc.name)
		result = {"role": doc.name, "document_number": number, "status": doc.status, "entity": entity}
		audit("entity_role_assigned", "NXR Entity Role", doc.name, payload_hash, correlation_id, result)
		complete_idempotency(idem, "NXR Entity Role", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


def transition_entity_role(
	role: str, status: str, idempotency_key: str, notes: str | None = None
) -> dict[str, Any]:
	require_action("manage_entity_role")
	target = str(status or "").strip().title()
	payload = {"role": role, "status": target, "notes": notes or ""}
	payload_hash = canonical_payload_hash(payload)
	correlation_id = correlation(payload)
	point = savepoint()
	try:
		idem, cached = start_idempotency(idempotency_key, payload_hash, correlation_id)
		if cached is not None:
			return cached
		doc = _lock("NXR Entity Role", role)
		try:
			assert_transition(str(doc.status), target, ROLE_TRANSITIONS)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		with service_write():
			doc.status = target
			doc.reviewed_by = frappe.session.user
			doc.reviewed_at = frappe.utils.now_datetime()
			doc.review_notes = notes or ""
			doc.save(ignore_permissions=True)
		result = {"role": doc.name, "document_number": doc.document_number, "status": doc.status}
		audit("entity_role_transitioned", "NXR Entity Role", doc.name, payload_hash, correlation_id, result)
		complete_idempotency(idem, "NXR Entity Role", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise
