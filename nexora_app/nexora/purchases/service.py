from __future__ import annotations

from typing import Any, Mapping

import frappe
from frappe import _

from nexora.directory.common import _resolve_chain
from nexora.directory.core import periods_overlap, validate_period
from nexora.directory.role_service import assign_entity_role, transition_entity_role
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
from nexora.purchases.core import (
	ACTIVE_COMPLIANCE_STATES,
	SUPPLIER_PROFILE_TRANSITIONS,
	assert_transition,
	normalize_classification,
)


def _required(data: Mapping[str, Any], fieldname: str, message: str) -> str:
	value = str(data.get(fieldname) or "").strip()
	if not value:
		frappe.throw(_(message))
	return value


def _lock(doctype: str, name: str) -> Any:
	table = frappe.qb.DocType(doctype)
	rows = (frappe.qb.from_(table).select(table.name).where(table.name == name).for_update()).run()
	if not rows:
		frappe.throw(_("El documento {0} no existe.").format(doctype))
	return frappe.get_doc(doctype, name)


def _canonical_entity(entity: str) -> str:
	canonical, _chain = _resolve_chain(entity)
	status = frappe.db.get_value("NXR Entity", canonical, "status")
	if status not in {"Active", "Blocked"}:
		frappe.throw(_("El proveedor debe derivar de una entidad activa o bloqueada."))
	return str(canonical)


def _supplier_role(entity: str, valid_from: str, valid_until: str | None, key: str) -> str:
	rows = frappe.get_all(
		"NXR Entity Role",
		filters={
			"entity": entity,
			"role_type": "Supplier",
			"status": ["in", ["Proposed", "Active", "Suspended"]],
		},
		fields=["name", "status"],
		limit=1,
	)
	if rows:
		role = str(rows[0].name)
		if rows[0].status != "Active":
			transition_entity_role(role, "Active", f"{key}:supplier-role-active")
		return role
	assigned = assign_entity_role(
		{
			"entity": entity,
			"role_type": "Supplier",
			"valid_from": valid_from,
			"valid_until": valid_until,
			"notes": "Rol creado por el expediente de proveedor NEXORA.",
			"idempotency_key": f"{key}:supplier-role",
		}
	)
	role = str(assigned["role"])
	transition_entity_role(role, "Active", f"{key}:supplier-role-active")
	return role


def _supplier_compliance(name: str | None, entity: str, *, require_current: bool) -> Any | None:
	value = str(name or "").strip()
	if not value:
		if require_current:
			frappe.throw(_("La activación requiere cumplimiento canónico de proveedor."))
		return None
	doc = (
		_lock("NXR Entity Compliance", value)
		if require_current
		else frappe.get_doc("NXR Entity Compliance", value)
	)
	canonical_compliance_entity, _chain = _resolve_chain(str(doc.entity))
	if canonical_compliance_entity != entity:
		frappe.throw(_("El cumplimiento debe pertenecer a la entidad canónica del proveedor."))
	if doc.compliance_type != "Supplier":
		frappe.throw(_("El expediente requiere cumplimiento de tipo Supplier."))
	if require_current and doc.status not in ACTIVE_COMPLIANCE_STATES:
		frappe.throw(_("El cumplimiento del proveedor debe estar vigente o exceptuado."))
	return doc


def _validate_compliance_coverage(profile: Any, compliance: Any) -> None:
	profile_start, profile_end = validate_period(profile.valid_from, profile.valid_until)
	compliance_start, compliance_end = validate_period(compliance.valid_from, compliance.valid_until)
	if compliance_start and profile_start and profile_start < compliance_start:
		frappe.throw(_("La vigencia del proveedor inicia antes que su cumplimiento."))
	if compliance_end and (not profile_end or profile_end > compliance_end):
		frappe.throw(_("La vigencia del proveedor excede la vigencia del cumplimiento."))


def _snapshot(doc: Any) -> dict[str, Any]:
	return {
		"profile": doc.name,
		"document_number": doc.document_number,
		"status": doc.status,
		"entity": doc.entity,
		"canonical_entity": _resolve_chain(str(doc.entity))[0],
		"entity_role": doc.entity_role,
		"classification": doc.classification,
		"valid_from": doc.valid_from,
		"valid_until": doc.valid_until,
		"compliance": doc.compliance,
		"compliance_status": doc.compliance_status,
		"evidence": doc.evidence,
	}


@frappe.whitelist(methods=["POST"])
def create_supplier_profile(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("manage_supplier")
	data = parse_payload(payload)
	entity = _canonical_entity(_required(data, "entity", "El perfil de proveedor requiere entidad."))
	valid_from = _required(data, "valid_from", "El perfil de proveedor requiere fecha inicial.")
	try:
		validate_period(valid_from, data.get("valid_until"))
		classification = normalize_classification(data.get("classification"))
	except ValueError as exc:
		frappe.throw(_(str(exc)))
	key = _required(data, "idempotency_key", "El perfil requiere clave de idempotencia.")
	compliance = _supplier_compliance(data.get("compliance"), entity, require_current=False)
	normalized = {
		**data,
		"entity": entity,
		"classification": classification,
		"compliance": compliance.name if compliance else None,
	}
	fingerprint = canonical_payload_hash(normalized)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		existing_profiles = frappe.get_all(
			"NXR Supplier Profile",
			filters={
				"entity": entity,
				"classification": classification,
				"status": ["in", ["Draft", "Active", "Suspended", "Expired"]],
			},
			fields=["name", "valid_from", "valid_until"],
		)
		for existing in existing_profiles:
			try:
				overlap = periods_overlap(
					valid_from, data.get("valid_until"), existing.valid_from, existing.valid_until
				)
			except ValueError as exc:
				frappe.throw(_(str(exc)))
			if overlap:
				frappe.throw(_("Ya existe un perfil de proveedor superpuesto para la clasificación."))
		role = _supplier_role(entity, valid_from, data.get("valid_until"), key)
		number, sequence = issue_document_number("NXR Supplier Profile", key)
		with service_write():
			doc = frappe.get_doc(
				{
					"doctype": "NXR Supplier Profile",
					"document_number": number,
					"entity": entity,
					"entity_role": role,
					"status": "Draft",
					"classification": classification,
					"valid_from": valid_from,
					"valid_until": data.get("valid_until"),
					"compliance": compliance.name if compliance else None,
					"compliance_status": compliance.status if compliance else "Pending",
					"evidence": compliance.evidence if compliance else None,
					"notes": data.get("notes"),
					"idempotency_key": key,
					"payload_hash": fingerprint,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
		link_sequence(sequence, doc.name)
		result = _snapshot(doc)
		audit(
			"supplier_profile_created", "NXR Supplier Profile", doc.name, fingerprint, correlation_id, result
		)
		complete_idempotency(idem, "NXR Supplier Profile", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def transition_supplier_profile(profile: str, status: str, idempotency_key: str) -> dict[str, Any]:
	require_action("manage_supplier")
	target = str(status or "").strip().title()
	payload = {"profile": profile, "status": target}
	fingerprint = canonical_payload_hash(payload)
	correlation_id = correlation(payload)
	point = savepoint()
	try:
		idem, cached = start_idempotency(idempotency_key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		doc = _lock("NXR Supplier Profile", profile)
		try:
			assert_transition(str(doc.status), target, SUPPLIER_PROFILE_TRANSITIONS)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		if target == "Active":
			if frappe.db.get_value("NXR Entity", doc.entity, "status") != "Active":
				frappe.throw(_("La entidad canónica debe estar activa para habilitar al proveedor."))
			today = frappe.utils.getdate()
			if frappe.utils.getdate(doc.valid_from) > today or (
				doc.valid_until and frappe.utils.getdate(doc.valid_until) < today
			):
				frappe.throw(_("La vigencia del proveedor no comprende la fecha actual."))
			compliance = _supplier_compliance(doc.compliance, str(doc.entity), require_current=True)
			_validate_compliance_coverage(doc, compliance)
			if frappe.db.get_value("NXR Entity Role", doc.entity_role, "status") != "Active":
				frappe.throw(_("El rol Supplier de la entidad debe estar activo."))
			with service_write():
				doc.compliance_status = compliance.status
				doc.evidence = compliance.evidence
		with service_write():
			doc.status = target
			doc.save(ignore_permissions=True)
		result = _snapshot(doc)
		audit(
			"supplier_profile_transitioned",
			"NXR Supplier Profile",
			doc.name,
			fingerprint,
			correlation_id,
			result,
		)
		complete_idempotency(idem, "NXR Supplier Profile", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["GET"])
def get_supplier_profile(profile: str) -> dict[str, Any]:
	require_action("read_purchases")
	return _snapshot(frappe.get_doc("NXR Supplier Profile", profile))


@frappe.whitelist(methods=["GET"])
def list_supplier_profiles(
	entity: str | None = None, status: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
	require_action("read_purchases")
	filters: dict[str, Any] = {}
	if entity:
		filters["entity"] = _resolve_chain(entity)[0]
	if status:
		filters["status"] = status
	rows = frappe.get_all(
		"NXR Supplier Profile",
		filters=filters,
		fields=["name"],
		order_by="modified desc",
		limit=min(max(int(limit or 100), 1), 500),
	)
	return [_snapshot(frappe.get_doc("NXR Supplier Profile", row.name)) for row in rows]
