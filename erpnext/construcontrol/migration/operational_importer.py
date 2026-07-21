from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Mapping
from typing import Any

import frappe
from frappe.utils import cint, escape_html, flt, getdate, now_datetime

from erpnext.construcontrol.controllers import (
	recalculate_contract,
	recalculate_funding_source,
	refresh_material_balance,
)
from erpnext.construcontrol.migration.schema import (
	canonical_json,
	iter_entities,
	normalize_export_document,
	preflight_snapshot,
	sanitize_payload,
	sha256_json,
	source_key,
	source_record_id,
	versioned_record_key,
)

ENTITY_DOCTYPES = {
	"settings": "CC Project Profile",
	"phases": "CC Construction Phase",
	"incomes": "CC Funding Source",
	"expenses": "CC Expense Control",
	"laborContracts": "CC Labor Contract",
	"materials": "CC Material Ledger",
	"inventoryMovements": "CC Inventory Movement",
	"progressUpdates": "CC Progress Update",
	"weeklyClosings": "CC Weekly Closing",
	"reports": "CC Generated Report",
	"notificationContacts": "CC Notification Contact",
	"notificationRules": "CC Notification Rule",
	"notificationLogs": "CC Notification Log",
	"auditLogs": "CC Audit Log",
	"userAccounts": "CC User Access",
	"procurementRequests": "CC Procurement Request",
	"equipmentRecords": "CC Equipment Control",
	"changeOrders": "CC Change Order",
	"approvalRequests": "CC Approval Request",
	"enterprisePlatform.projects": "CC Project Profile",
	"enterprisePlatform.permissionOverrides": "CC User Permission Override",
	"enterprisePlatform.partners": "CC Business Partner Profile",
	"enterprisePlatform.catalog": "CC Catalog Profile",
	"enterprisePlatform.payables": "CC Payable Control",
	"enterprisePlatform.documentTemplates": "CC Document Template",
	"enterprisePlatform.automationRules": "CC Automation Rule",
	"enterprisePlatform.automationExecutions": "CC Automation Execution",
	"enterprisePlatform.dailyLogs": "CC Daily Site Log",
	"enterprisePlatform.crewMembers": "CC Crew Member",
	"enterprisePlatform.crewAttendance": "CC Crew Attendance",
	"enterprisePlatform.tools": "CC Equipment Control",
	"enterprisePlatform.toolLoans": "CC Tool Loan",
	"enterprisePlatform.safetyIncidents": "CC Safety Incident",
	"enterprisePlatform.signatures": "CC Digital Signature",
	"enterprisePlatform.immutableAudit": "CC Immutable Audit Event",
	"enterprisePlatform.backupHistory": "CC Backup Snapshot",
}


def _json(value: Any) -> str:
	return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str)


def _date(value: Any) -> Any:
	try:
		return getdate(str(value)[:10]) if value else None
	except Exception:
		return None


def _deleted(record: Mapping[str, Any]) -> int:
	deletion = record.get("deletion")
	return cint(isinstance(deletion, Mapping) and deletion.get("deleted"))


def _company(settings: Any) -> str | None:
	return settings.get("default_company") or frappe.db.get_single_value("Global Defaults", "default_company")


def _ensure_project(project_key: str, snapshot: Mapping[str, Any], settings: Any) -> tuple[str | None, bool]:
	configured = settings.get("default_project")
	if configured and frappe.db.exists("Project", configured):
		return configured, False
	company = _company(settings)
	if not company:
		return None, False
	source = snapshot.get("settings") if isinstance(snapshot.get("settings"), Mapping) else {}
	project_name = str(source.get("projectName") or project_key).strip()
	existing = frappe.db.get_value("Project", {"project_name": project_name, "company": company}, "name")
	if existing:
		return existing, False
	phases = snapshot.get("phases") if isinstance(snapshot.get("phases"), list) else []
	progress = [flt(row.get("progressPercent")) for row in phases if isinstance(row, Mapping)]
	doc = frappe.get_doc(
		{
			"doctype": "Project",
			"naming_series": "PROJ-.####",
			"project_name": project_name,
			"company": company,
			"status": "Open",
			"is_active": "Yes",
			"percent_complete_method": "Manual",
			"percent_complete": sum(progress) / len(progress) if progress else 0,
			"expected_start_date": _date(source.get("projectStartDate")),
			"notes": _json({"legacy_project_key": project_key}),
		}
	).insert(ignore_permissions=True)
	return doc.name, True


def _ensure_task(
	project: str | None, record: Mapping[str, Any], company: str | None
) -> tuple[str | None, bool]:
	if not project:
		return None, False
	subject = str(record.get("name") or record.get("title") or record.get("id") or "Fase de obra").strip()
	existing = frappe.db.get_value("Task", {"project": project, "subject": subject}, "name")
	if existing:
		return existing, False
	status = {
		"active": "Working",
		"next": "Open",
		"pending": "Open",
		"paused": "Pending Review",
		"completed": "Completed",
	}.get(str(record.get("status")), "Open")
	doc = frappe.get_doc(
		{
			"doctype": "Task",
			"subject": subject,
			"project": project,
			"company": company,
			"status": status,
			"progress": flt(record.get("progressPercent")),
			"exp_start_date": _date(record.get("targetStartDate")),
			"exp_end_date": _date(record.get("targetEndDate")),
			"description": str(record.get("description") or ""),
		}
	).insert(ignore_permissions=True)
	return doc.name, True


def _ensure_supplier(name: Any, record: Mapping[str, Any]) -> tuple[str | None, bool]:
	supplier_name = str(name or "").strip()
	if not supplier_name or supplier_name.upper() in {"N/A", "NA", "NINGUNO"}:
		return None, False
	existing = frappe.db.get_value("Supplier", {"supplier_name": supplier_name}, "name")
	if existing:
		return existing, False
	group = frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")
	if not group:
		return None, False
	doc = frappe.get_doc(
		{
			"doctype": "Supplier",
			"supplier_name": supplier_name,
			"supplier_group": group,
			"supplier_type": "Individual" if record.get("identity") else "Company",
			"tax_id": record.get("taxId"),
		}
	).insert(ignore_permissions=True)
	return doc.name, True


def _ensure_contract(
	record: Mapping[str, Any], project: str | None, supplier: str | None
) -> tuple[str | None, bool]:
	if not supplier:
		return None, False
	number = str(record.get("contractNumber") or record.get("id") or "").strip()
	existing = (
		frappe.db.get_value(
			"Contract", {"party_type": "Supplier", "party_name": supplier, "signee": number}, "name"
		)
		if number
		else None
	)
	if existing:
		return existing, False
	safe, _ = sanitize_payload(record)
	doc = frappe.get_doc(
		{
			"doctype": "Contract",
			"party_type": "Supplier",
			"party_name": supplier,
			"status": "Unsigned" if record.get("status") == "draft" else "Active",
			"start_date": _date(record.get("startDate")),
			"end_date": _date(record.get("targetEndDate")),
			"signee": number or None,
			"contract_terms": f"<pre>{escape_html(_json(safe))}</pre>",
			"document_type": "Project" if project else None,
			"document_name": project,
		}
	).insert(ignore_permissions=True)
	return doc.name, True


def _ensure_item(record: Mapping[str, Any]) -> tuple[str | None, bool]:
	raw = str(record.get("code") or record.get("id") or record.get("name") or sha256_json(record)[:12])
	code = f"CC-{re.sub(r'[^A-Za-z0-9_-]+','-',raw).strip('-')}"[:140]
	if frappe.db.exists("Item", code):
		return code, False
	group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
	uom = frappe.db.get_value("UOM", record.get("unit"), "name") or frappe.db.get_value("UOM", "Nos", "name")
	if not group or not uom:
		return None, False
	doc = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": code,
			"item_name": str(record.get("name") or record.get("title") or code),
			"description": str(record.get("description") or ""),
			"item_group": group,
			"stock_uom": uom,
			"is_stock_item": 1,
			"is_purchase_item": 1,
			"is_sales_item": 0,
		}
	).insert(ignore_permissions=True)
	return doc.name, True


def _evidence(record: Mapping[str, Any]) -> list[dict[str, Any]]:
	result: list[dict[str, Any]] = []
	seen: set[str] = set()

	def walk(value: Any) -> None:
		if isinstance(value, list):
			for item in value:
				walk(item)
		elif isinstance(value, Mapping):
			if (
				value.get("_file_omitted")
				or ((value.get("name") or value.get("id")) and (value.get("type") or value.get("size")))
			) and (value.get("name") or value.get("id")):
				key = str(value.get("id") or value.get("name"))
				if key not in seen:
					seen.add(key)
					result.append(
						{
							"id": value.get("id"),
							"name": value.get("name"),
							"type": value.get("type"),
							"size": value.get("size"),
							"uploadedAt": value.get("uploadedAt"),
						}
					)
			for item in value.values():
				walk(item)

	walk(record)
	return result


def validate_payload(payload: Any) -> dict[str, Any]:
	projects = normalize_export_document(payload)
	counts: Counter[str] = Counter()
	errors: list[str] = []
	warnings: list[str] = []
	totals = {"income_hnl": 0.0, "expense_hnl": 0.0, "contract_hnl": 0.0}
	evidence_references = 0
	for project in projects:
		report = preflight_snapshot(project.snapshot)
		counts.update(report.get("counts") or {})
		for issue in report.get("issues") or []:
			text = f"{project.project_key}: {issue.get('code')} {issue.get('entity','')} {issue.get('source_id','')}".strip()
			(errors if issue.get("severity") == "error" else warnings).append(text)
		for entity, _index, record in iter_entities(project.snapshot):
			if entity == "incomes" and not _deleted(record) and record.get("status") == "received":
				totals["income_hnl"] += flt(record.get("amountHnl"))
			elif (
				entity == "expenses"
				and not _deleted(record)
				and record.get("status") != "pending"
				and record.get("financialStatus") not in {"cancelled", "reimbursed"}
			):
				totals["expense_hnl"] += flt(record.get("amountHnl"))
			elif entity == "laborContracts" and not _deleted(record) and record.get("status") != "cancelled":
				totals["contract_hnl"] += flt(record.get("projectValueHnl") or record.get("laborValueHnl"))
			evidence_references += len(_evidence(record))
	return {
		"valid": not errors,
		"projects": len(projects),
		"counts": dict(sorted(counts.items())),
		"errors": errors,
		"warnings": warnings,
		"totals": {k: round(v, 2) for k, v in totals.items()},
		"evidence_references": evidence_references,
		"images_imported": 0,
	}


def _legacy(
	run: str, project_key: str, entity: str, index: int, record: Mapping[str, Any]
) -> tuple[Any, bool]:
	sid = project_key if entity == "settings" else source_record_id(record, index)
	safe, _ = sanitize_payload(record)
	payload_hash = sha256_json(safe)
	key = versioned_record_key(project_key, entity, sid, payload_hash)
	if frappe.db.exists("ConstruControl Legacy Record", key):
		return frappe.get_doc("ConstruControl Legacy Record", key), False
	doc = frappe.get_doc(
		{
			"doctype": "ConstruControl Legacy Record",
			"record_key": key,
			"migration_run": run,
			"project_key": project_key,
			"entity_type": entity,
			"source_id": sid,
			"payload_hash": payload_hash,
			"migration_status": "Preserved",
			"source_created_at": record.get("createdAt"),
			"source_updated_at": record.get("updatedAt"),
			"is_deleted": _deleted(record),
			"raw_payload": canonical_json(safe),
		}
	).insert(ignore_permissions=True)
	return doc, True


def _upsert(doctype: str, key: str, values: dict[str, Any]) -> tuple[str, bool]:
	allowed = {field.fieldname for field in frappe.get_meta(doctype).fields}
	clean = {name: value for name, value in values.items() if name in allowed and value is not None}
	clean["source_key"] = key
	existing = frappe.db.get_value(doctype, {"source_key": key}, "name")
	if existing:
		doc = frappe.get_doc(doctype, existing)
		for name, value in clean.items():
			doc.set(name, value)
		doc.save(ignore_permissions=True)
		return doc.name, False
	clean["doctype"] = doctype
	return frappe.get_doc(clean).insert(ignore_permissions=True).name, True


def _base(record: Mapping[str, Any], sid: str, project: str | None) -> dict[str, Any]:
	safe, _ = sanitize_payload(record)
	return {
		"source_id": sid,
		"project": project,
		"code": record.get("code") or sid,
		"title": record.get("title") or record.get("name") or record.get("description") or sid,
		"status": record.get("status") or "active",
		"posting_date": _date(record.get("date") or record.get("createdAt") or record.get("updatedAt")),
		"amount_hnl": flt(record.get("amountHnl") or record.get("totalHnl") or record.get("valueHnl")),
		"description": record.get("description") or record.get("notes"),
		"payload_json": _json(safe),
		"is_logically_deleted": _deleted(record),
	}


def _values(entity: str, record: Mapping[str, Any], sid: str, c: dict[str, Any]) -> dict[str, Any]:
	base = _base(record, sid, c["project"])
	if entity == "settings":
		return {
			**base,
			"source_id": c["project_key"],
			"project_code": record.get("projectCode") or "PRJ-0001",
			"project_name": record.get("projectName") or c["project_key"],
			"owner_name": record.get("ownerName"),
			"address": record.get("address"),
			"start_date": _date(record.get("projectStartDate")),
			"target_end_date": _date(record.get("projectTargetEndDate")),
			"original_budget_hnl": flt(record.get("originalBudgetHnl")),
			"is_current": 1,
			"document_prefix": record.get("documentPrefix"),
			"currency": record.get("currency") or "HNL",
			"timezone": record.get("timezone"),
			"approval_required": cint(record.get("approvalRequired")),
		}
	if entity == "phases":
		return {
			**base,
			"task": c["tasks"].get(sid),
			"phase_order": cint(record.get("order")),
			"phase_name": record.get("name") or sid,
			"risk": record.get("risk"),
			"budget_hnl": flt(record.get("budgetHnl")),
			"progress_percent": flt(record.get("progressPercent")),
			"responsible": record.get("responsible"),
			"target_start_date": _date(record.get("targetStartDate")),
			"target_end_date": _date(record.get("targetEndDate")),
			"checklist_json": _json(record.get("checklist") or []),
			"logs_json": _json(record.get("logs") or []),
			"expected_actions_json": _json(record.get("expectedActions") or []),
		}
	if entity == "incomes":
		amount = flt(record.get("amountHnl"))
		return {
			**base,
			"income_type": record.get("type") or "other",
			"date_sent": _date(record.get("dateSent")),
			"date_received": _date(record.get("dateReceived")),
			"currency": record.get("currency") or "HNL",
			"original_amount": flt(record.get("originalAmount")),
			"exchange_rate": flt(record.get("exchangeRate")) or 1,
			"amount_hnl": amount,
			"spent_hnl": 0,
			"pending_hnl": 0,
			"available_hnl": amount,
			"projected_hnl": amount,
			"sender": record.get("sender"),
			"origin_country": record.get("originCountry"),
			"remittance_company": record.get("remittanceCompany"),
			"bank": record.get("bank"),
			"reference": record.get("reference"),
			"notes": record.get("notes"),
			"evidence_metadata_json": _json(_evidence(record)),
		}
	if entity == "laborContracts":
		value = flt(record.get("projectValueHnl") or record.get("laborValueHnl"))
		return {
			**base,
			"phase": c["phases"].get(str(record.get("phaseId"))),
			"contract": c["native_contracts"].get(sid),
			"contract_code": record.get("contractNumber") or sid,
			"contractor_name": record.get("contractorName") or "Contratista sin nombre",
			"supplier": c["contract_suppliers"].get(sid),
			"start_date": _date(record.get("startDate")),
			"target_end_date": _date(record.get("targetEndDate")),
			"project_scope": record.get("projectScope"),
			"contract_mode": record.get("contractMode") or record.get("contractType") or "other",
			"project_value_hnl": value,
			"labor_value_hnl": flt(record.get("laborValueHnl")),
			"paid_hnl": 0,
			"balance_hnl": value,
			"materials_included": record.get("materialsIncluded"),
			"materials_not_included": record.get("materialsNotIncluded"),
			"notes": record.get("notes"),
			"evidence_metadata_json": _json(_evidence(record)),
		}
	if entity == "expenses":
		return {
			**base,
			"phase": c["phases"].get(str(record.get("phaseId"))),
			"posting_date": _date(record.get("date")) or getdate(),
			"folio": record.get("folio"),
			"category": record.get("category") or "other",
			"subcategory": record.get("subcategory"),
			"commercial_source": record.get("commercialSource")
			or record.get("source")
			or record.get("category"),
			"unit": record.get("unit") or "UNIDAD",
			"quantity": flt(record.get("quantity")) or 1,
			"description": record.get("description") or record.get("title") or sid,
			"provider_name": record.get("providerName") or "Proveedor no especificado",
			"supplier": c["expense_suppliers"].get(sid),
			"payment_method": record.get("paymentMethod"),
			"amount_hnl": flt(record.get("amountHnl")),
			"funding_source": c["incomes"].get(str(record.get("paymentSourceId"))),
			"labor_contract": c["contracts"].get(str(record.get("laborContractId"))),
			"labor_payment_type": record.get("laborPaymentType"),
			"financial_status": record.get("financialStatus") or record.get("status"),
			"document_status": record.get("documentStatus"),
			"approval_status": record.get("approvalStatus"),
			"notes": record.get("notes"),
			"document_json": _json(record.get("document") or {}),
			"evidence_metadata_json": _json(_evidence(record)),
		}
	if entity == "materials":
		return {
			**base,
			"item": c["native_items"].get(sid),
			"material_name": record.get("name") or record.get("title") or sid,
			"unit": record.get("unit") or "UNIDAD",
			"initial_qty": flt(record.get("initialQty") or record.get("quantity")),
			"current_qty": flt(record.get("initialQty") or record.get("quantity")),
			"unit_cost_hnl": flt(record.get("unitCostHnl")),
			"low_stock_threshold": flt(record.get("lowStockThreshold")),
			"stock_status": "available",
		}
	if entity == "inventoryMovements":
		return {
			**base,
			"material": c["materials"].get(str(record.get("materialId"))),
			"movement_type": record.get("type") or "consumption",
			"quantity": flt(record.get("quantity")),
			"unit": record.get("unit"),
			"phase": c["phases"].get(str(record.get("phaseId"))),
			"reference": record.get("reference"),
		}
	if entity == "progressUpdates":
		return {
			**base,
			"phase": c["phases"].get(str(record.get("phaseId"))),
			"progress_percent": flt(record.get("progressPercent")),
			"moment": record.get("moment"),
			"quality": record.get("quality"),
			"responsible": record.get("responsible"),
			"location": record.get("location"),
		}
	if entity == "weeklyClosings":
		snap = record.get("snapshot") if isinstance(record.get("snapshot"), Mapping) else {}
		return {
			**base,
			"week_start": _date(record.get("weekStart")),
			"week_end": _date(record.get("weekEnd")),
			"initial_balance_hnl": flt(snap.get("initialBalanceHnl")),
			"income_hnl": flt(snap.get("incomeHnl")),
			"expense_hnl": flt(snap.get("expenseHnl")),
			"final_balance_hnl": flt(snap.get("finalBalanceHnl")),
		}
	if entity == "auditLogs":
		return {
			**base,
			"actor": record.get("actor") or record.get("createdBy"),
			"action": record.get("action") or "legacy_event",
			"record_type": record.get("recordType"),
			"record_id": record.get("recordId"),
			"previous_state": record.get("previousState"),
			"next_state": record.get("nextState"),
			"reason": record.get("reason"),
		}
	if entity == "userAccounts":
		return {
			**base,
			"email": record.get("email"),
			"display_name": record.get("name") or record.get("displayName"),
			"role_name": record.get("role"),
			"access_status": record.get("status"),
			"provider": record.get("provider"),
			"is_protected": cint(record.get("isProtected")),
		}
	return {
		**base,
		"phase": c["phases"].get(str(record.get("phaseId"))),
		"actor": record.get("actor"),
		"action": record.get("action"),
		"record_type": record.get("recordType"),
		"record_id": record.get("recordId"),
		"email": record.get("email"),
		"display_name": record.get("name") or record.get("displayName"),
		"role_name": record.get("role"),
	}


def _evidence_docs(
	project: str | None,
	project_key: str,
	entity: str,
	sid: str,
	doctype: str,
	target: str,
	record: Mapping[str, Any],
) -> int:
	created = 0
	for index, item in enumerate(_evidence(record)):
		identifier = str(item.get("id") or item.get("name") or index)
		key = source_key(project_key, "evidence", f"{entity}:{sid}:{identifier}")
		_name, made = _upsert(
			"CC Evidence",
			key,
			{
				"source_id": identifier,
				"project": project,
				"code": identifier,
				"title": item.get("name") or f"Evidencia {index+1}",
				"status": "omitted",
				"description": "Solo se conservó metadata; el archivo no fue importado por decisión del propietario.",
				"related_doctype": doctype,
				"related_name": target,
				"original_name": item.get("name"),
				"mime_type": item.get("type"),
				"size_bytes": cint(item.get("size")),
				"source_reference": f"{entity}/{sid}",
				"file_imported": 0,
				"omission_reason": "Las imágenes y fotografías fueron excluidas por decisión del propietario.",
				"payload_json": _json(item),
			},
		)
		created += cint(made)
	return created


def run_import(payload: Any, run_name: str, dry_run: bool = True) -> dict[str, Any]:
	validation = validate_payload(payload)
	if not validation["valid"]:
		raise ValueError("El respaldo no supera la validación: " + "; ".join(validation["errors"]))
	if dry_run:
		return {
			"dry_run": True,
			"validation": validation,
			"input_counts": validation["counts"],
			"output_counts": {},
			"created": 0,
			"updated": 0,
		}
	settings = frappe.get_cached_doc("ConstruControl Settings")
	output: Counter[str] = Counter()
	created = updated = legacy_created = evidence_created = 0
	for source_project in normalize_export_document(payload):
		project_key, snapshot = source_project.project_key, source_project.snapshot
		project, made = _ensure_project(project_key, snapshot, settings)
		created += cint(made)
		c: dict[str, Any] = {
			"project_key": project_key,
			"project": project,
			"company": _company(settings),
			"tasks": {},
			"phases": {},
			"incomes": {},
			"contracts": {},
			"native_contracts": {},
			"contract_suppliers": {},
			"expense_suppliers": {},
			"materials": {},
			"native_items": {},
		}
		for i, row in enumerate(
			snapshot.get("phases", []) if isinstance(snapshot.get("phases"), list) else []
		):
			if isinstance(row, Mapping):
				sid = source_record_id(row, i)
				c["tasks"][sid], made = _ensure_task(project, row, c["company"])
				created += cint(made)
		for i, row in enumerate(
			snapshot.get("laborContracts", []) if isinstance(snapshot.get("laborContracts"), list) else []
		):
			if isinstance(row, Mapping):
				sid = source_record_id(row, i)
				supplier, m1 = _ensure_supplier(row.get("contractorName"), row)
				native, m2 = _ensure_contract(row, project, supplier)
				c["contract_suppliers"][sid], c["native_contracts"][sid] = supplier, native
				created += cint(m1) + cint(m2)
		for i, row in enumerate(
			snapshot.get("expenses", []) if isinstance(snapshot.get("expenses"), list) else []
		):
			if isinstance(row, Mapping):
				sid = source_record_id(row, i)
				c["expense_suppliers"][sid], made = _ensure_supplier(row.get("providerName"), row)
				created += cint(made)
		for i, row in enumerate(
			snapshot.get("materials", []) if isinstance(snapshot.get("materials"), list) else []
		):
			if isinstance(row, Mapping):
				sid = source_record_id(row, i)
				c["native_items"][sid], made = _ensure_item(row)
				created += cint(made)
		entities = list(iter_entities(snapshot))
		priority = {
			"settings": 0,
			"phases": 1,
			"incomes": 2,
			"laborContracts": 3,
			"materials": 4,
			"expenses": 5,
			"inventoryMovements": 6,
		}
		entities.sort(key=lambda row: (priority.get(row[0], 50), row[1]))
		for entity, index, record in entities:
			doctype = ENTITY_DOCTYPES.get(entity)
			if not doctype:
				continue
			sid = project_key if entity == "settings" else source_record_id(record, index)
			legacy, made_legacy = _legacy(run_name, project_key, entity, index, record)
			legacy_created += cint(made_legacy)
			target, made = _upsert(
				doctype, source_key(project_key, entity, sid), _values(entity, record, sid, c)
			)
			created += cint(made)
			updated += cint(not made)
			output[entity] += 1
			legacy.db_set(
				{
					"migration_status": "Mapped",
					"target_doctype": doctype,
					"target_name": target,
					"created_by_migration": cint(made),
				},
				update_modified=False,
			)
			if entity == "phases":
				c["phases"][sid] = target
			elif entity == "incomes":
				c["incomes"][sid] = target
			elif entity == "laborContracts":
				c["contracts"][sid] = target
			elif entity == "materials":
				c["materials"][sid] = target
			evidence_created += _evidence_docs(project, project_key, entity, sid, doctype, target, record)
		for name in c["incomes"].values():
			if name:
				recalculate_funding_source(name)
		for name in c["contracts"].values():
			if name:
				recalculate_contract(name)
		for name in frappe.get_all("CC Material Ledger", filters={"project": project}, pluck="name"):
			refresh_material_balance(name)
	expected = {key: count for key, count in validation["counts"].items() if key in ENTITY_DOCTYPES}
	mismatches = {
		key: {"input": count, "output": output.get(key, 0)}
		for key, count in expected.items()
		if output.get(key, 0) != count
	}
	if mismatches:
		raise ValueError("La conciliación de cantidades falló: " + _json(mismatches))
	return {
		"dry_run": False,
		"validation": validation,
		"input_counts": validation["counts"],
		"output_counts": dict(sorted(output.items())),
		"created": created,
		"updated": updated,
		"legacy_created": legacy_created,
		"evidence_metadata_created": evidence_created,
		"images_imported": 0,
		"completed_at": now_datetime(),
	}
