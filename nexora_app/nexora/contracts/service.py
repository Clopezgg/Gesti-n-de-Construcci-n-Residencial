from __future__ import annotations

from typing import Any, Mapping

import frappe
from frappe import _

from nexora.contracts.core import (
	AMENDMENT_TRANSITIONS,
	CONTRACT_TRANSITIONS,
	ESTIMATE_TRANSITIONS,
	PROFILE_TRANSITIONS,
	amendment_balances,
	assert_transition,
	ensure_available,
	estimate_amounts,
	line_amounts,
	money,
	validate_amendment,
	validate_period,
)
from nexora.directory.common import _resolve_chain
from nexora.directory.core import periods_overlap
from nexora.directory.role_service import assign_entity_role, transition_entity_role
from nexora.financial.analytics import execute_central_operation
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


def _validated_evidence(name: str | None, project: str | None = None) -> str | None:
	value = str(name or "").strip()
	if not value:
		return None
	doc = frappe.get_doc("NXR Evidence", value)
	if doc.status != "Validated":
		frappe.throw(_("La evidencia contractual debe estar validada."))
	if project and doc.project != project:
		frappe.throw(_("La evidencia contractual debe pertenecer al proyecto del contrato."))
	return doc.name


def _canonical_entity(entity: str) -> str:
	canonical, _chain = _resolve_chain(entity)
	status = frappe.db.get_value("NXR Entity", canonical, "status")
	if status not in {"Active", "Blocked"}:
		frappe.throw(_("El contratista debe ser una entidad activa o bloqueada."))
	return canonical


def _profile_role(entity: str, valid_from: str, valid_until: str | None, key: str) -> str:
	role = frappe.db.get_value(
		"NXR Entity Role",
		{
			"entity": entity,
			"role_type": "Contractor",
			"status": ["in", ["Proposed", "Active", "Suspended"]],
		},
		"name",
	)
	if role:
		return str(role)
	assigned = assign_entity_role(
		{
			"entity": entity,
			"role_type": "Contractor",
			"valid_from": valid_from,
			"valid_until": valid_until,
			"notes": "Rol creado por el expediente contractual NEXORA.",
			"idempotency_key": f"{key}:contractor-role",
		}
	)
	role = str(assigned["role"])
	transition_entity_role(role, "Active", f"{key}:contractor-role-active")
	return role


def _contract_snapshot(doc: Any) -> dict[str, Any]:
	return {
		"name": doc.name,
		"document_number": doc.document_number,
		"status": doc.status,
		"contractor": doc.contractor,
		"canonical_contractor": _resolve_chain(doc.contractor)[0],
		"contractor_profile": doc.contractor_profile,
		"modality": doc.modality,
		"project": doc.project,
		"cost_center": doc.cost_center,
		"fund_source": doc.fund_source,
		"responsible": doc.responsible,
		"scope": doc.scope,
		"current_scope": doc.current_scope,
		"currency": doc.currency,
		"exchange_rate": str(money(doc.exchange_rate)),
		"original_labor_amount": str(money(doc.original_labor_amount)),
		"original_material_amount": str(money(doc.original_material_amount)),
		"original_amount": str(money(doc.original_amount)),
		"current_labor_amount": str(money(doc.current_labor_amount)),
		"current_material_amount": str(money(doc.current_material_amount)),
		"current_amount": str(money(doc.current_amount)),
		"executed_labor_amount": str(money(doc.executed_labor_amount)),
		"executed_material_amount": str(money(doc.executed_material_amount)),
		"executed_amount": str(money(doc.executed_amount)),
		"pending_amount": str(money(doc.pending_amount)),
		"paid_amount": str(money(doc.paid_amount)),
		"advance_disbursed": str(money(doc.advance_disbursed)),
		"advance_amortized": str(money(doc.advance_amortized)),
		"advance_balance": str(money(doc.advance_balance)),
		"retention_held": str(money(doc.retention_held)),
		"retention_returned": str(money(doc.retention_returned)),
		"retention_balance": str(money(doc.retention_balance)),
		"fine_amount": str(money(doc.fine_amount)),
		"deduction_amount": str(money(doc.deduction_amount)),
		"start_date": doc.start_date,
		"original_end_date": doc.original_end_date,
		"current_end_date": doc.current_end_date,
		"version": int(doc.version or 0),
	}


def _contract_evidence(rows: list[Mapping[str, Any]], project: str) -> list[dict[str, Any]]:
	result = []
	for row in rows:
		evidence = _validated_evidence(str(row.get("evidence") or ""), project)
		result.append(
			{
				"evidence_type": _required(row, "evidence_type", "Cada documento contractual requiere tipo."),
				"evidence": evidence,
				"reference": row.get("reference"),
				"issuer": row.get("issuer"),
				"valid_from": row.get("valid_from"),
				"valid_until": row.get("valid_until"),
				"amount": row.get("amount") or 0,
				"status": row.get("status") or "Valid",
			}
		)
	return result


def _ensure_activation_documents(doc: Any) -> None:
	types = {row.evidence_type for row in doc.evidence_rows if row.status == "Valid"}
	missing = sorted({"Contract", "Signature", "Approval"} - types)
	if missing:
		frappe.throw(_("Faltan documentos para activar el contrato: {0}.").format(", ".join(missing)))
	if not doc.signed_on or not doc.owner_signatory or not doc.contractor_signatory:
		frappe.throw(_("La activación requiere fecha y firmantes del contrato."))


def _transaction(
	contract: Any,
	transaction_type: str,
	amount: object,
	key: str,
	*,
	estimate: str | None = None,
	operation: str | None = None,
	evidence: str | None = None,
	notes: str | None = None,
	reference_transaction: str | None = None,
	correction_operation: str | None = None,
) -> Any:
	number, sequence = issue_document_number("NXR Contract Transaction", key)
	with service_write():
		doc = frappe.get_doc(
			{
				"doctype": "NXR Contract Transaction",
				"document_number": number,
				"contract": contract.name,
				"estimate": estimate,
				"transaction_type": transaction_type,
				"status": "Executed",
				"transaction_date": frappe.utils.today(),
				"currency": contract.currency,
				"amount": money(amount),
				"operation": operation,
				"reference_transaction": reference_transaction,
				"correction_operation": correction_operation,
				"evidence": evidence,
				"notes": notes,
				"idempotency_key": key,
				"payload_hash": canonical_payload_hash(
					{
						"contract": contract.name,
						"estimate": estimate,
						"transaction_type": transaction_type,
						"amount": str(money(amount)),
						"operation": operation,
						"reference_transaction": reference_transaction,
						"correction_operation": correction_operation,
					}
				),
				"correlation_id": getattr(contract, "correlation_id", None),
			}
		).insert(ignore_permissions=True)
	link_sequence(sequence, doc.name)
	return doc


def _operation_payload(
	contract: Any,
	data: Mapping[str, Any],
	*,
	key: str,
	operation_code: str,
	economic_category: str,
	amount: object,
	evidence: str | None,
	reference_name: str | None = None,
) -> dict[str, Any]:
	amount_hnl = money(money(amount) * money(contract.exchange_rate))
	payload: dict[str, Any] = {
		"idempotency_key": key,
		"operation_code": operation_code,
		"economic_category": economic_category,
		"project": contract.project,
		"amount_hnl": amount_hnl,
		"allocations": data.get("allocations")
		or (
			[
				{
					"source": contract.fund_source,
					"amount_hnl": amount_hnl,
				}
			]
			if contract.fund_source
			else []
		),
		"cost_center": contract.cost_center,
		"beneficiary_doctype": "NXR Entity",
		"beneficiary": contract.contractor,
		"requester": data.get("requester"),
		"approved_by": data.get("approved_by"),
		"payment_method": data.get("payment_method"),
		"external_reference": data.get("external_reference"),
		"operation_date": data.get("operation_date") or frappe.utils.today(),
		"evidence": evidence,
		"description": data.get("description") or f"Movimiento contractual {contract.document_number}",
	}
	if data.get("due_date"):
		payload["due_date"] = data.get("due_date")
	if reference_name:
		payload.update({"reference_doctype": "NXR Operation", "reference_name": reference_name})
	return payload


@frappe.whitelist(methods=["POST"])
def create_contractor_profile(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("manage_contract")
	data = parse_payload(payload)
	entity = _canonical_entity(_required(data, "entity", "El perfil requiere entidad."))
	valid_from = _required(data, "valid_from", "El perfil requiere fecha inicial.")
	try:
		validate_period(valid_from, data.get("valid_until"))
	except ValueError as exc:
		frappe.throw(_(str(exc)))
	key = _required(data, "idempotency_key", "El perfil requiere clave de idempotencia.")
	fingerprint = canonical_payload_hash({**data, "entity": entity})
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		existing_profiles = frappe.get_all(
			"NXR Contractor Profile",
			filters={
				"entity": entity,
				"classification": data.get("classification") or "Other",
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
				frappe.throw(_("Ya existe un perfil de contratista superpuesto para la misma clasificación."))
		_profile_role(entity, valid_from, data.get("valid_until"), key)
		evidence = _validated_evidence(data.get("evidence"))
		number, sequence = issue_document_number("NXR Contractor Profile", key)
		with service_write():
			doc = frappe.get_doc(
				{
					"doctype": "NXR Contractor Profile",
					"document_number": number,
					"entity": entity,
					"status": "Draft",
					"classification": data.get("classification") or "Other",
					"valid_from": valid_from,
					"valid_until": data.get("valid_until"),
					"compliance_status": data.get("compliance_status") or "Pending",
					"evidence": evidence,
					"notes": data.get("notes"),
					"idempotency_key": key,
					"payload_hash": fingerprint,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
		link_sequence(sequence, doc.name)
		result = {"profile": doc.name, "document_number": number, "entity": entity, "status": doc.status}
		audit(
			"contractor_profile_created",
			"NXR Contractor Profile",
			doc.name,
			fingerprint,
			correlation_id,
			result,
		)
		complete_idempotency(idem, "NXR Contractor Profile", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def transition_contractor_profile(profile: str, status: str, idempotency_key: str) -> dict[str, Any]:
	require_action("manage_contract")
	target = str(status or "").strip()
	payload = {"profile": profile, "status": target}
	fingerprint = canonical_payload_hash(payload)
	correlation_id = correlation(payload)
	point = savepoint()
	try:
		idem, cached = start_idempotency(idempotency_key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		doc = _lock("NXR Contractor Profile", profile)
		try:
			assert_transition(str(doc.status), target, PROFILE_TRANSITIONS)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		if target == "Active":
			if doc.compliance_status not in {"Valid", "Exception Approved"}:
				frappe.throw(_("El perfil requiere cumplimiento válido o excepción aprobada."))
			today = frappe.utils.getdate()
			if frappe.utils.getdate(doc.valid_from) > today or (
				doc.valid_until and frappe.utils.getdate(doc.valid_until) < today
			):
				frappe.throw(_("La vigencia del perfil no comprende la fecha actual."))
		with service_write():
			doc.status = target
			doc.save(ignore_permissions=True)
		result = {"profile": doc.name, "document_number": doc.document_number, "status": doc.status}
		audit(
			"contractor_profile_transitioned",
			"NXR Contractor Profile",
			doc.name,
			fingerprint,
			correlation_id,
			result,
		)
		complete_idempotency(idem, "NXR Contractor Profile", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def create_contract(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("create_contract")
	data = parse_payload(payload)
	key = _required(data, "idempotency_key", "El contrato requiere clave de idempotencia.")
	contractor = _canonical_entity(_required(data, "contractor", "El contrato requiere contratista."))
	profile = _required(data, "contractor_profile", "El contrato requiere expediente de contratista.")
	profile_doc = _lock("NXR Contractor Profile", profile)
	if profile_doc.entity != contractor or profile_doc.status != "Active":
		frappe.throw(_("El expediente de contratista debe estar activo y pertenecer a la entidad canónica."))
	project = _required(data, "project", "El contrato requiere proyecto.")
	if not frappe.db.exists("Project", project):
		frappe.throw(_("El proyecto contractual no existe."))
	cost_center = _required(data, "cost_center", "El contrato requiere centro de costo.")
	if not frappe.db.exists("Cost Center", cost_center):
		frappe.throw(_("El centro de costo contractual no existe."))
	source = str(data.get("fund_source") or "").strip() or None
	if source and frappe.db.get_value("NXR Fund Source", source, "project") != project:
		frappe.throw(_("La fuente principal debe pertenecer al proyecto del contrato."))
	lines = [dict(row) for row in (data.get("lines") or [])]
	for line in lines:
		line["cost_center"] = line.get("cost_center") or cost_center
		line["fund_source"] = line.get("fund_source") or source
		if (
			line.get("fund_source")
			and frappe.db.get_value("NXR Fund Source", line["fund_source"], "project") != project
		):
			frappe.throw(_("Cada fuente de línea debe pertenecer al proyecto contractual."))
	try:
		amounts = line_amounts(lines)
		validate_period(data.get("start_date"), data.get("end_date"))
	except ValueError as exc:
		frappe.throw(_(str(exc)))
	evidence_rows = _contract_evidence(list(data.get("evidence_rows") or []), project)
	normalized = {**data, "contractor": contractor, "lines": lines, "evidence_rows": evidence_rows}
	fingerprint = canonical_payload_hash(normalized)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		number, sequence = issue_document_number("NXR Contract", key)
		scope = _required(data, "scope", "El contrato requiere alcance.")
		with service_write():
			doc = frappe.get_doc(
				{
					"doctype": "NXR Contract",
					"document_number": number,
					"status": "Draft",
					"contractor": contractor,
					"contractor_profile": profile,
					"modality": data.get("modality") or "Other",
					"project": project,
					"cost_center": cost_center,
					"fund_source": source,
					"responsible": _required(data, "responsible", "El contrato requiere responsable."),
					"scope": scope,
					"current_scope": scope,
					"currency": data.get("currency") or "HNL",
					"exchange_rate": data.get("exchange_rate") or 1,
					"original_labor_amount": amounts.labor,
					"original_material_amount": amounts.materials,
					"original_amount": amounts.total,
					"current_labor_amount": amounts.labor,
					"current_material_amount": amounts.materials,
					"current_amount": amounts.total,
					"start_date": data.get("start_date"),
					"original_end_date": data.get("end_date"),
					"current_end_date": data.get("end_date"),
					"signed_on": data.get("signed_on"),
					"owner_signatory": data.get("owner_signatory"),
					"contractor_signatory": data.get("contractor_signatory"),
					"version": 1,
					"lines": lines,
					"evidence_rows": evidence_rows,
					"executed_labor_amount": 0,
					"executed_material_amount": 0,
					"paid_amount": 0,
					"advance_disbursed": 0,
					"advance_amortized": 0,
					"advance_balance": 0,
					"retention_held": 0,
					"retention_returned": 0,
					"retention_balance": 0,
					"fine_amount": 0,
					"deduction_amount": 0,
					"idempotency_key": key,
					"payload_hash": fingerprint,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
		link_sequence(sequence, doc.name)
		result = {
			"contract": doc.name,
			"document_number": number,
			"status": doc.status,
			"amounts": _contract_snapshot(doc),
		}
		audit("contract_created", "NXR Contract", doc.name, fingerprint, correlation_id, result)
		complete_idempotency(idem, "NXR Contract", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def transition_contract(
	contract: str,
	status: str,
	idempotency_key: str,
	reason: str | None = None,
) -> dict[str, Any]:
	require_action("manage_contract")
	target = str(status or "").strip()
	payload = {"contract": contract, "status": target, "reason": reason or ""}
	fingerprint = canonical_payload_hash(payload)
	correlation_id = correlation(payload)
	point = savepoint()
	try:
		idem, cached = start_idempotency(idempotency_key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		doc = _lock("NXR Contract", contract)
		try:
			assert_transition(str(doc.status), target, CONTRACT_TRANSITIONS)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		if target == "Active":
			if doc.status == "Suspended":
				frappe.throw(_("La reactivación debe ejecutarse mediante una adenda versionada."))
			_ensure_activation_documents(doc)
		if target in {"Suspended", "Early Terminated"}:
			frappe.throw(
				_("La suspensión o terminación anticipada debe ejecutarse mediante una adenda versionada.")
			)
		if target == "Cancelled Before Active" and not str(reason or "").strip():
			frappe.throw(_("La transición contractual requiere motivo."))
		if target == "In Liquidation" and money(doc.current_amount) != money(
			doc.executed_labor_amount
		) + money(doc.executed_material_amount):
			frappe.throw(_("La liquidación requiere que el monto vigente esté completamente ejecutado."))
		if target == "Liquidated" and (money(doc.advance_balance) or money(doc.retention_balance)):
			frappe.throw(_("La liquidación exige anticipos y retenciones conciliados."))
		with service_write():
			doc.status = target
			if target == "Approved":
				doc.approved_by = frappe.session.user
				doc.approved_at = frappe.utils.now_datetime()
			if target == "Suspended":
				doc.suspension_reason = reason
			doc.save(ignore_permissions=True)
		if target == "Liquidated":
			_transaction(doc, "Liquidation", 0, f"{idempotency_key}:liquidation", notes=reason)
		result = {
			"contract": doc.name,
			"document_number": doc.document_number,
			"status": doc.status,
			"amounts": _contract_snapshot(doc),
		}
		audit("contract_transitioned", "NXR Contract", doc.name, fingerprint, correlation_id, result)
		complete_idempotency(idem, "NXR Contract", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def create_contract_amendment(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("manage_contract")
	data = parse_payload(payload)
	key = _required(data, "idempotency_key", "La adenda requiere clave de idempotencia.")
	contract = _required(data, "contract", "La adenda requiere contrato.")
	contract_doc = _lock("NXR Contract", contract)
	if contract_doc.status not in {"Active", "Suspended"}:
		frappe.throw(_("Solo un contrato activo o suspendido admite adendas."))
	amendment_type = _required(data, "amendment_type", "La adenda requiere tipo.")
	evidence = _validated_evidence(data.get("evidence"), contract_doc.project)
	if not evidence:
		frappe.throw(_("La adenda requiere evidencia validada."))
	try:
		validate_amendment(
			amendment_type,
			labor_delta=data.get("labor_delta"),
			materials_delta=data.get("material_delta"),
			current_status=str(contract_doc.status),
			current_end_date=contract_doc.current_end_date,
			new_end_date=data.get("new_end_date"),
			scope_change=data.get("scope_change"),
		)
		if amendment_type in {"Increase", "Reduction"}:
			amendment_balances(
				contract_doc.current_labor_amount,
				contract_doc.current_material_amount,
				data.get("labor_delta"),
				data.get("material_delta"),
				contract_doc.executed_labor_amount,
				contract_doc.executed_material_amount,
			)
		if data.get("new_end_date"):
			validate_period(contract_doc.start_date, data.get("new_end_date"))
	except ValueError as exc:
		frappe.throw(_(str(exc)))
	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		version = int(contract_doc.version or 1) + 1
		number, sequence = issue_document_number("NXR Contract Amendment", key)
		with service_write():
			doc = frappe.get_doc(
				{
					"doctype": "NXR Contract Amendment",
					"document_number": number,
					"contract": contract_doc.name,
					"version": version,
					"status": "Draft",
					"amendment_type": amendment_type,
					"effective_date": data.get("effective_date") or frappe.utils.today(),
					"currency": contract_doc.currency,
					"labor_delta": data.get("labor_delta") or 0,
					"material_delta": data.get("material_delta") or 0,
					"new_end_date": data.get("new_end_date"),
					"scope_change": data.get("scope_change"),
					"reason": _required(data, "reason", "La adenda requiere motivo."),
					"evidence": evidence,
					"idempotency_key": key,
					"payload_hash": fingerprint,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
		link_sequence(sequence, doc.name)
		result = {"amendment": doc.name, "document_number": number, "version": version, "status": doc.status}
		audit(
			"contract_amendment_created",
			"NXR Contract Amendment",
			doc.name,
			fingerprint,
			correlation_id,
			result,
		)
		complete_idempotency(idem, "NXR Contract Amendment", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def transition_contract_amendment(amendment: str, status: str, idempotency_key: str) -> dict[str, Any]:
	require_action("manage_contract")
	target = str(status or "").strip()
	payload = {"amendment": amendment, "status": target}
	fingerprint = canonical_payload_hash(payload)
	correlation_id = correlation(payload)
	point = savepoint()
	try:
		idem, cached = start_idempotency(idempotency_key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		doc = _lock("NXR Contract Amendment", amendment)
		try:
			assert_transition(str(doc.status), target, AMENDMENT_TRANSITIONS)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		contract = _lock("NXR Contract", doc.contract)
		if target == "Active":
			balances = amendment_balances(
				contract.current_labor_amount,
				contract.current_material_amount,
				doc.labor_delta,
				doc.material_delta,
				contract.executed_labor_amount,
				contract.executed_material_amount,
			)
			with service_write():
				contract.current_labor_amount = balances.labor
				contract.current_material_amount = balances.materials
				contract.current_amount = balances.total
				contract.current_end_date = doc.new_end_date or contract.current_end_date
				if doc.scope_change:
					contract.current_scope = doc.scope_change
				contract.version = doc.version
				if doc.amendment_type == "Suspension":
					contract.status = "Suspended"
					contract.suspension_reason = doc.reason
				elif doc.amendment_type == "Reactivation":
					contract.status = "Active"
					contract.suspension_reason = None
				elif doc.amendment_type == "Early Termination":
					contract.status = "Early Terminated"
				contract.save(ignore_permissions=True)
		with service_write():
			doc.status = target
			if target == "Approved":
				doc.approved_by = frappe.session.user
				doc.approved_at = frappe.utils.now_datetime()
			if target == "Active":
				doc.applied_at = frappe.utils.now_datetime()
			doc.save(ignore_permissions=True)
		result = {
			"amendment": doc.name,
			"document_number": doc.document_number,
			"status": doc.status,
			"contract": _contract_snapshot(contract),
		}
		audit(
			"contract_amendment_transitioned",
			"NXR Contract Amendment",
			doc.name,
			fingerprint,
			correlation_id,
			result,
		)
		complete_idempotency(idem, "NXR Contract Amendment", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def create_contract_estimate(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("create_contract")
	data = parse_payload(payload)
	key = _required(data, "idempotency_key", "La estimación requiere clave de idempotencia.")
	contract = _lock("NXR Contract", _required(data, "contract", "La estimación requiere contrato."))
	if contract.status != "Active":
		frappe.throw(_("Solo un contrato activo admite estimaciones."))
	cost_kind = _required(data, "cost_kind", "La estimación requiere tipo de costo.")
	lines = [dict(row) for row in (data.get("lines") or [])]
	if not lines:
		frappe.throw(_("La estimación requiere líneas."))
	contract_lines = {row.line_code: row for row in contract.lines}
	gross = money(0)
	for row in lines:
		code = _required(row, "contract_line", "Cada estimación requiere línea contractual.")
		original = contract_lines.get(code)
		if not original:
			frappe.throw(_("La línea contractual {0} no existe.").format(code))
		if original.cost_kind != cost_kind or str(row.get("cost_kind") or cost_kind) != cost_kind:
			frappe.throw(_("La estimación no puede mezclar tipos de costo."))
		row["cost_kind"] = cost_kind
		gross += money(row.get("amount"))
	values = estimate_amounts(
		gross,
		data.get("advance_amortization"),
		data.get("retention_amount"),
		data.get("fine_amount"),
		data.get("deduction_amount"),
	)
	available = (
		money(contract.current_labor_amount) - money(contract.executed_labor_amount)
		if cost_kind == "Labor"
		else money(contract.current_material_amount) - money(contract.executed_material_amount)
	)
	ensure_available(values.gross, available, "bruto de estimación")
	if values.advance_amortization > money(contract.advance_balance):
		frappe.throw(_("La amortización supera el saldo anticipado."))
	evidence = _validated_evidence(data.get("evidence"), contract.project)
	if not evidence:
		frappe.throw(_("La estimación requiere evidencia validada."))
	try:
		validate_period(data.get("period_start"), data.get("period_end"))
	except ValueError as exc:
		frappe.throw(_(str(exc)))
	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		sequence = int(frappe.db.count("NXR Contract Estimate", {"contract": contract.name})) + 1
		number, number_sequence = issue_document_number("NXR Contract Estimate", key)
		with service_write():
			doc = frappe.get_doc(
				{
					"doctype": "NXR Contract Estimate",
					"document_number": number,
					"contract": contract.name,
					"status": "Draft",
					"estimate_sequence": sequence,
					"period_start": data.get("period_start"),
					"period_end": data.get("period_end"),
					"cost_kind": cost_kind,
					"currency": contract.currency,
					"lines": lines,
					"gross_amount": values.gross,
					"advance_amortization": values.advance_amortization,
					"retention_amount": values.retention,
					"fine_amount": values.fine,
					"deduction_amount": values.deduction,
					"payable_amount": values.payable,
					"evidence": evidence,
					"requester": data.get("requester") or frappe.session.user,
					"idempotency_key": key,
					"payload_hash": fingerprint,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
		link_sequence(number_sequence, doc.name)
		result = {
			"estimate": doc.name,
			"document_number": number,
			"status": doc.status,
			"gross_amount": str(values.gross),
			"payable_amount": str(values.payable),
		}
		audit(
			"contract_estimate_created",
			"NXR Contract Estimate",
			doc.name,
			fingerprint,
			correlation_id,
			result,
		)
		complete_idempotency(idem, "NXR Contract Estimate", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def transition_contract_estimate(estimate: str, status: str, idempotency_key: str) -> dict[str, Any]:
	require_action("manage_contract")
	target = str(status or "").strip()
	payload = {"estimate": estimate, "status": target}
	fingerprint = canonical_payload_hash(payload)
	correlation_id = correlation(payload)
	point = savepoint()
	try:
		idem, cached = start_idempotency(idempotency_key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		doc = _lock("NXR Contract Estimate", estimate)
		try:
			assert_transition(str(doc.status), target, ESTIMATE_TRANSITIONS)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		with service_write():
			doc.status = target
			if target == "Approved":
				doc.approved_by = frappe.session.user
				doc.approved_at = frappe.utils.now_datetime()
			doc.save(ignore_permissions=True)
		result = {"estimate": doc.name, "document_number": doc.document_number, "status": doc.status}
		audit(
			"contract_estimate_transitioned",
			"NXR Contract Estimate",
			doc.name,
			fingerprint,
			correlation_id,
			result,
		)
		complete_idempotency(idem, "NXR Contract Estimate", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def disburse_contract_advance(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("execute_contract")
	data = parse_payload(payload)
	key = _required(data, "idempotency_key", "El anticipo requiere clave de idempotencia.")
	contract = _lock("NXR Contract", _required(data, "contract", "El anticipo requiere contrato."))
	if contract.status != "Active":
		frappe.throw(_("Solo un contrato activo admite anticipos."))
	amount = money(data.get("amount"))
	ensure_available(
		amount, money(contract.current_amount) - money(contract.advance_disbursed), "de anticipo"
	)
	evidence = _validated_evidence(data.get("evidence"), contract.project)
	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		operation = execute_central_operation(
			_operation_payload(
				contract,
				data,
				key=f"{key}:operation",
				operation_code="ADVANCE_DISBURSEMENT",
				economic_category="ADVANCE",
				amount=amount,
				evidence=evidence,
			)
		)
		with service_write():
			contract.advance_disbursed = money(contract.advance_disbursed) + amount
			contract.advance_balance = money(contract.advance_disbursed) - money(contract.advance_amortized)
			contract.save(ignore_permissions=True)
		movement = _transaction(
			contract,
			"Advance",
			amount,
			f"{key}:transaction",
			operation=str(operation["operation"]),
			evidence=evidence,
		)
		result = {
			"contract": contract.name,
			"operation": operation["operation"],
			"transaction": movement.name,
			"advance_balance": str(money(contract.advance_balance)),
		}
		audit(
			"contract_advance_disbursed", "NXR Contract", contract.name, fingerprint, correlation_id, result
		)
		complete_idempotency(idem, "NXR Contract", contract.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def execute_contract_estimate_payment(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("execute_contract")
	data = parse_payload(payload)
	key = _required(data, "idempotency_key", "El pago requiere clave de idempotencia.")
	estimate = _lock("NXR Contract Estimate", _required(data, "estimate", "El pago requiere estimación."))
	if estimate.status != "Approved":
		frappe.throw(_("Solo una estimación aprobada puede pagarse."))
	contract = _lock("NXR Contract", estimate.contract)
	if contract.status != "Active":
		frappe.throw(_("El pago requiere contrato activo."))
	values = estimate_amounts(
		estimate.gross_amount,
		estimate.advance_amortization,
		estimate.retention_amount,
		estimate.fine_amount,
		estimate.deduction_amount,
	)
	available = (
		money(contract.current_labor_amount) - money(contract.executed_labor_amount)
		if estimate.cost_kind == "Labor"
		else money(contract.current_material_amount) - money(contract.executed_material_amount)
	)
	ensure_available(values.gross, available, "bruto de estimación")
	if values.advance_amortization > money(contract.advance_balance):
		frappe.throw(_("La amortización supera el saldo anticipado."))
	evidence = _validated_evidence(estimate.evidence, contract.project)
	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		payment_operation = None
		if values.payable > 0:
			payment = execute_central_operation(
				_operation_payload(
					contract,
					data,
					key=f"{key}:payment-operation",
					operation_code="CONSTRUCTION_PAYMENT",
					economic_category=(
						"CONSTRUCTION_LABOR" if estimate.cost_kind == "Labor" else "CONSTRUCTION_MATERIALS"
					),
					amount=values.payable,
					evidence=evidence,
				)
			)
			payment_operation = str(payment["operation"])
			_transaction(
				contract,
				"Payment",
				values.payable,
				f"{key}:payment-transaction",
				estimate=estimate.name,
				operation=payment_operation,
				evidence=evidence,
			)
		settlement_operation = None
		if values.advance_amortization > 0:
			advance_operation = _required(
				data, "advance_operation", "La amortización requiere la operación de anticipo."
			)
			settlement = execute_central_operation(
				_operation_payload(
					contract,
					data,
					key=f"{key}:settlement-operation",
					operation_code="ADVANCE_SETTLEMENT",
					economic_category=(
						"CONSTRUCTION_LABOR" if estimate.cost_kind == "Labor" else "CONSTRUCTION_MATERIALS"
					),
					amount=values.advance_amortization,
					evidence=evidence,
					reference_name=advance_operation,
				)
			)
			settlement_operation = str(settlement["operation"])
			_transaction(
				contract,
				"Advance Amortization",
				values.advance_amortization,
				f"{key}:settlement-transaction",
				estimate=estimate.name,
				operation=settlement_operation,
				evidence=evidence,
			)
		for transaction_type, amount in (
			("Retention", values.retention),
			("Fine", values.fine),
			("Deduction", values.deduction),
		):
			if amount > 0:
				_transaction(
					contract,
					transaction_type,
					amount,
					f"{key}:{transaction_type.lower()}-transaction",
					estimate=estimate.name,
					evidence=evidence,
				)
		with service_write():
			if estimate.cost_kind == "Labor":
				contract.executed_labor_amount = money(contract.executed_labor_amount) + values.gross
			else:
				contract.executed_material_amount = money(contract.executed_material_amount) + values.gross
			contract.paid_amount = money(contract.paid_amount) + values.payable
			contract.advance_amortized = money(contract.advance_amortized) + values.advance_amortization
			contract.advance_balance = money(contract.advance_disbursed) - money(contract.advance_amortized)
			contract.retention_held = money(contract.retention_held) + values.retention
			contract.retention_balance = money(contract.retention_held) - money(contract.retention_returned)
			contract.fine_amount = money(contract.fine_amount) + values.fine
			contract.deduction_amount = money(contract.deduction_amount) + values.deduction
			contract.save(ignore_permissions=True)
			estimate.status = "Paid"
			estimate.operation = payment_operation
			estimate.advance_operation = data.get("advance_operation")
			estimate.paid_at = frappe.utils.now_datetime()
			estimate.save(ignore_permissions=True)
		result = {
			"contract": contract.name,
			"estimate": estimate.name,
			"payment_operation": payment_operation,
			"settlement_operation": settlement_operation,
			"amounts": _contract_snapshot(contract),
		}
		audit(
			"contract_estimate_paid",
			"NXR Contract Estimate",
			estimate.name,
			fingerprint,
			correlation_id,
			result,
		)
		complete_idempotency(idem, "NXR Contract Estimate", estimate.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def return_contract_retention(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("execute_contract")
	data = parse_payload(payload)
	key = _required(data, "idempotency_key", "La devolución requiere clave de idempotencia.")
	contract = _lock("NXR Contract", _required(data, "contract", "La devolución requiere contrato."))
	amount = money(data.get("amount"))
	ensure_available(amount, contract.retention_balance, "de retención")
	evidence = _validated_evidence(data.get("evidence"), contract.project)
	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		operation = execute_central_operation(
			_operation_payload(
				contract,
				data,
				key=f"{key}:operation",
				operation_code="CONSTRUCTION_PAYMENT",
				economic_category="CONSTRUCTION_LABOR",
				amount=amount,
				evidence=evidence,
			)
		)
		with service_write():
			contract.retention_returned = money(contract.retention_returned) + amount
			contract.retention_balance = money(contract.retention_held) - money(contract.retention_returned)
			contract.paid_amount = money(contract.paid_amount) + amount
			contract.save(ignore_permissions=True)
		movement = _transaction(
			contract,
			"Retention Return",
			amount,
			f"{key}:transaction",
			operation=str(operation["operation"]),
			evidence=evidence,
		)
		result = {
			"contract": contract.name,
			"operation": operation["operation"],
			"transaction": movement.name,
			"retention_balance": str(money(contract.retention_balance)),
		}
		audit(
			"contract_retention_returned", "NXR Contract", contract.name, fingerprint, correlation_id, result
		)
		complete_idempotency(idem, "NXR Contract", contract.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def correct_contract_transaction(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("execute_contract")
	data = parse_payload(payload)
	key = _required(data, "idempotency_key", "La corrección requiere clave de idempotencia.")
	original = _lock(
		"NXR Contract Transaction",
		_required(data, "transaction", "La corrección requiere movimiento contractual original."),
	)
	if original.status != "Executed" or not original.operation:
		frappe.throw(_("Solo un movimiento ejecutado con operación central puede corregirse."))
	correction_code = _required(data, "correction_operation", "La corrección requiere tipo.")
	if correction_code not in {"REAL_RETURN", "REVERSAL_NO_CASH", "DOCUMENT_SUBSTITUTION"}:
		frappe.throw(_("Tipo de corrección contractual no permitido."))
	contract = _lock("NXR Contract", original.contract)
	evidence = _validated_evidence(data.get("evidence"), contract.project)
	amount = money(data.get("amount") if correction_code == "REAL_RETURN" else 0)
	if correction_code == "REAL_RETURN":
		prior_returns = money(
			frappe.db.get_value(
				"NXR Contract Transaction",
				{
					"reference_transaction": original.name,
					"correction_operation": "REAL_RETURN",
					"status": "Executed",
				},
				"sum(amount)",
			)
			or 0
		)
		ensure_available(amount, money(original.amount) - prior_returns, "de devolución real")
		if not evidence:
			frappe.throw(_("La devolución real requiere evidencia validada."))
	if correction_code == "DOCUMENT_SUBSTITUTION" and not evidence:
		frappe.throw(_("La sustitución documental requiere evidencia validada."))
	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		operation_payload = _operation_payload(
			contract,
			data,
			key=f"{key}:operation",
			operation_code=correction_code,
			economic_category={
				"REAL_RETURN": "RETURN",
				"REVERSAL_NO_CASH": "REVERSAL",
				"DOCUMENT_SUBSTITUTION": "DOCUMENTARY",
			}[correction_code],
			amount=amount,
			evidence=evidence,
			reference_name=original.operation,
		)
		operation = execute_central_operation(operation_payload)
		with service_write():
			if correction_code == "REAL_RETURN":
				if original.transaction_type == "Payment":
					contract.paid_amount = money(contract.paid_amount) - amount
				elif original.transaction_type == "Advance":
					contract.advance_disbursed = money(contract.advance_disbursed) - amount
					if money(contract.advance_disbursed) < money(contract.advance_amortized):
						frappe.throw(
							_("La devolución no puede dejar el anticipo por debajo de lo amortizado.")
						)
					contract.advance_balance = money(contract.advance_disbursed) - money(
						contract.advance_amortized
					)
				elif original.transaction_type == "Retention Return":
					contract.retention_returned = money(contract.retention_returned) - amount
					contract.retention_balance = money(contract.retention_held) - money(
						contract.retention_returned
					)
					contract.paid_amount = money(contract.paid_amount) - amount
				else:
					frappe.throw(_("Este tipo de movimiento no admite devolución real contractual."))
				if (
					min(
						money(contract.paid_amount),
						money(contract.advance_disbursed),
						money(contract.retention_returned),
					)
					< 0
				):
					frappe.throw(_("La corrección produciría un saldo contractual negativo."))
				contract.save(ignore_permissions=True)
			if correction_code == "REVERSAL_NO_CASH" or (
				correction_code == "REAL_RETURN" and money(prior_returns + amount) == money(original.amount)
			):
				original.status = "Reversed"
				original.save(ignore_permissions=True)
		movement = _transaction(
			contract,
			"Correction",
			amount,
			f"{key}:transaction",
			operation=str(operation["operation"]),
			evidence=evidence,
			notes=data.get("reason"),
			reference_transaction=original.name,
			correction_operation=correction_code,
		)
		result = {
			"contract": contract.name,
			"original_transaction": original.name,
			"correction_transaction": movement.name,
			"operation": operation["operation"],
			"correction_operation": correction_code,
			"amounts": _contract_snapshot(contract),
		}
		audit(
			"contract_transaction_corrected",
			"NXR Contract Transaction",
			original.name,
			fingerprint,
			correlation_id,
			result,
		)
		complete_idempotency(idem, "NXR Contract Transaction", movement.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def get_contract(contract: str) -> dict[str, Any]:
	require_action("read_contracts")
	doc = frappe.get_doc("NXR Contract", contract)
	result = _contract_snapshot(doc)
	result.update(
		{
			"lines": [row.as_dict() for row in doc.lines],
			"evidence_rows": [row.as_dict() for row in doc.evidence_rows],
			"amendments": frappe.get_all(
				"NXR Contract Amendment",
				filters={"contract": doc.name},
				fields=[
					"name",
					"document_number",
					"version",
					"status",
					"amendment_type",
					"effective_date",
					"labor_delta",
					"material_delta",
					"new_end_date",
				],
				order_by="version desc",
			),
			"estimates": frappe.get_all(
				"NXR Contract Estimate",
				filters={"contract": doc.name},
				fields=[
					"name",
					"document_number",
					"estimate_sequence",
					"status",
					"cost_kind",
					"gross_amount",
					"payable_amount",
					"operation",
				],
				order_by="estimate_sequence desc",
			),
			"transactions": frappe.get_all(
				"NXR Contract Transaction",
				filters={"contract": doc.name},
				fields=[
					"name",
					"document_number",
					"transaction_type",
					"transaction_date",
					"amount",
					"operation",
					"estimate",
					"reference_transaction",
					"correction_operation",
				],
				order_by="creation desc",
			),
		}
	)
	return result


@frappe.whitelist(methods=["POST"])
def list_contracts(
	project: str | None = None, contractor: str | None = None, status: str | None = None, limit: int = 50
) -> list[dict[str, Any]]:
	require_action("read_contracts")
	filters: dict[str, Any] = {}
	if project:
		filters["project"] = project
	if status:
		filters["status"] = status
	rows = frappe.get_all(
		"NXR Contract",
		filters=filters or None,
		fields=[
			"name",
			"document_number",
			"status",
			"contractor",
			"modality",
			"project",
			"current_amount",
			"executed_amount",
			"pending_amount",
			"paid_amount",
			"advance_balance",
			"retention_balance",
			"current_end_date",
			"version",
		],
		order_by="creation desc",
		limit_page_length=200,
	)
	if contractor:
		canonical = _resolve_chain(contractor)[0]
		rows = [row for row in rows if _resolve_chain(str(row.contractor))[0] == canonical]
	return rows[: min(max(int(limit or 50), 1), 200)]
