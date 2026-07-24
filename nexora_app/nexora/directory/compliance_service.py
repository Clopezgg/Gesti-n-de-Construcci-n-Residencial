from __future__ import annotations

from typing import Any, Mapping

import frappe
from frappe import _

from nexora.directory.common import COMPLIANCE_TYPES, _lock, _required, _validated_evidence
from nexora.directory.core import COMPLIANCE_TRANSITIONS, assert_transition, validate_period
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


def create_entity_compliance(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("manage_entity_compliance")
	data = parse_payload(payload)
	entity = _required(data, "entity", "El cumplimiento requiere entidad.")
	compliance_type = _required(data, "compliance_type", "El cumplimiento requiere tipo.").title()
	if compliance_type not in COMPLIANCE_TYPES:
		frappe.throw(_("Tipo de cumplimiento no permitido."))
	try:
		validate_period(data.get("valid_from"), data.get("valid_until"))
	except ValueError as exc:
		frappe.throw(_(str(exc)))
	idempotency_key = _required(data, "idempotency_key", "El cumplimiento requiere clave de idempotencia.")
	payload_hash = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(idempotency_key, payload_hash, correlation_id)
		if cached is not None:
			return cached
		entity_doc = _lock("NXR Entity", entity)
		if entity_doc.status == "Consolidated":
			frappe.throw(_("Registre el cumplimiento sobre la entidad canónica destino."))
		evidence = _validated_evidence(data.get("evidence")) if data.get("evidence") else None
		number, sequence = issue_document_number("NXR Entity Compliance", idempotency_key)
		with service_write():
			doc = frappe.get_doc(
				{
					"doctype": "NXR Entity Compliance",
					"document_number": number,
					"status": "Pending",
					"entity": entity,
					"compliance_type": compliance_type,
					"valid_from": data.get("valid_from"),
					"valid_until": data.get("valid_until"),
					"evidence": evidence,
					"notes": data.get("notes"),
					"created_by_user": frappe.session.user,
					"created_at": frappe.utils.now_datetime(),
					"idempotency_key": idempotency_key,
					"payload_hash": payload_hash,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
		link_sequence(sequence, doc.name)
		result = {"compliance": doc.name, "document_number": number, "status": doc.status, "entity": entity}
		audit(
			"entity_compliance_created",
			"NXR Entity Compliance",
			doc.name,
			payload_hash,
			correlation_id,
			result,
		)
		complete_idempotency(idem, "NXR Entity Compliance", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


def transition_entity_compliance(
	compliance: str, status: str, idempotency_key: str, notes: str | None = None, evidence: str | None = None
) -> dict[str, Any]:
	require_action("manage_entity_compliance")
	target = str(status or "").strip().title()
	payload = {"compliance": compliance, "status": target, "notes": notes or "", "evidence": evidence}
	payload_hash = canonical_payload_hash(payload)
	correlation_id = correlation(payload)
	point = savepoint()
	try:
		idem, cached = start_idempotency(idempotency_key, payload_hash, correlation_id)
		if cached is not None:
			return cached
		doc = _lock("NXR Entity Compliance", compliance)
		try:
			assert_transition(str(doc.status), target, COMPLIANCE_TRANSITIONS)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		validated_evidence = _validated_evidence(evidence) if evidence else doc.evidence
		if doc.evidence and evidence and doc.evidence != validated_evidence:
			frappe.throw(_("La evidencia existente no puede sustituirse silenciosamente."))
		if target in {"Current", "Approved Exception"} and not validated_evidence:
			frappe.throw(_("La transición vigente o exceptuada requiere evidencia validada."))
		with service_write():
			if not doc.evidence and validated_evidence:
				doc.evidence = validated_evidence
			doc.status = target
			doc.reviewed_by = frappe.session.user
			doc.reviewed_at = frappe.utils.now_datetime()
			doc.review_notes = notes or ""
			doc.save(ignore_permissions=True)
		result = {"compliance": doc.name, "document_number": doc.document_number, "status": doc.status}
		audit(
			"entity_compliance_transitioned",
			"NXR Entity Compliance",
			doc.name,
			payload_hash,
			correlation_id,
			result,
		)
		complete_idempotency(idem, "NXR Entity Compliance", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise
