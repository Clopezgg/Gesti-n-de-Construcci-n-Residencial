from __future__ import annotations

import base64
import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, escape_html, flt, getdate, now_datetime
from frappe.utils.file_manager import save_file

from erpnext.construcontrol.migration.schema import (
	aggregate_counts,
	canonical_json,
	evidence_manifest,
	iter_entities,
	normalize_export_document,
	preflight_snapshot,
	sanitize_payload,
	sha256_json,
	source_key,
	source_record_id,
	versioned_record_key,
)


MAX_EVIDENCE_BYTES = 12 * 1024 * 1024
STANDARD_MODE = "Create Draft Standard Documents"
ROLE_MAP = {
	"admin": "ConstruControl Manager",
	"auditor": "ConstruControl Auditor",
	"consultant": "ConstruControl Viewer",
	"operator": "ConstruControl Operator",
	"viewer": "ConstruControl Viewer",
}


def _json(value: Any) -> str:
	return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str)


def _date(value: Any) -> Any:
	if not value:
		return None
	try:
		return getdate(str(value)[:10])
	except Exception:
		return None


def _datetime(value: Any) -> Any:
	if not value:
		return None
	return str(value).replace("Z", "+00:00")


def _deleted(record: Mapping[str, Any]) -> int:
	deletion = record.get("deletion")
	return cint(isinstance(deletion, Mapping) and deletion.get("deleted"))


def _settings_doc() -> Any:
	return frappe.get_cached_doc("ConstruControl Settings")


def _company(settings: Any) -> str | None:
	return settings.default_company or frappe.db.get_single_value("Global Defaults", "default_company")


def _first_leaf(doctype: str, group_field: str | None = None) -> str | None:
	filters = {group_field: 0} if group_field else None
	return frappe.db.get_value(doctype, filters, "name", order_by="creation asc")


def _ensure_project(
	project_key: str, snapshot: Mapping[str, Any], settings: Any
) -> tuple[str | None, bool]:
	configured = settings.default_project
	if configured and frappe.db.exists("Project", configured):
		return configured, False
	company = _company(settings)
	if not company:
		return None, False
	source_settings = snapshot.get("settings", {})
	project_name = str(source_settings.get("projectName") or project_key).strip()
	existing = frappe.db.get_value("Project", {"project_name": project_name, "company": company}, "name")
	if existing:
		return existing, False
	phases = snapshot.get("phases", []) if isinstance(snapshot.get("phases"), list) else []
	progress_values = [flt(item.get("progressPercent")) for item in phases if isinstance(item, Mapping)]
	doc = frappe.get_doc(
		{
			"doctype": "Project",
			"naming_series": "PROJ-.####",
			"project_name": project_name,
			"company": company,
			"status": "Open",
			"is_active": "Yes",
			"percent_complete_method": "Manual",
			"percent_complete": sum(progress_values) / len(progress_values) if progress_values else 0,
			"notes": _json({"legacy_project_key": project_key, "settings": source_settings}),
		}
	).insert(ignore_permissions=True)
	return doc.name, True


def _ensure_task(project: str | None, record: Mapping[str, Any], company: str | None) -> tuple[str | None, bool]:
	if not project:
		return None, False
	subject = str(record.get("name") or record.get("title") or record.get("id") or "Legacy phase").strip()
	existing = frappe.db.get_value("Task", {"project": project, "subject": subject}, "name")
	if existing:
		return existing, False
	status_map = {
		"active": "Working",
		"next": "Open",
		"pending": "Open",
		"paused": "Pending Review",
		"completed": "Completed",
	}
	doc = frappe.get_doc(
		{
			"doctype": "Task",
			"subject": subject,
			"project": project,
			"company": company,
			"status": status_map.get(str(record.get("status")), "Open"),
			"progress": flt(record.get("progressPercent")),
			"exp_start_date": _date(record.get("targetStartDate")),
			"exp_end_date": _date(record.get("targetEndDate")),
			"description": str(record.get("description") or record.get("notes") or ""),
		}
	).insert(ignore_permissions=True)
	return doc.name, True


def _ensure_supplier(name: Any, record: Mapping[str, Any] | None = None) -> tuple[str | None, bool]:
	supplier_name = str(name or "").strip()
	if not supplier_name:
		return None, False
	existing = frappe.db.get_value("Supplier", {"supplier_name": supplier_name}, "name")
	if existing:
		return existing, False
	record = record or {}
	supplier_group = frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")
	doc = frappe.get_doc(
		{
			"doctype": "Supplier",
			"supplier_name": supplier_name,
			"supplier_group": supplier_group,
			"supplier_type": "Individual" if record.get("identity") else "Company",
			"tax_id": record.get("taxId") or record.get("tax_id"),
			"supplier_details": _json(record),
		}
	).insert(ignore_permissions=True)
	return doc.name, True


def _item_code(prefix: str, record: Mapping[str, Any]) -> str:
	raw = str(record.get("code") or record.get("id") or record.get("name") or sha256_json(record)[:12])
	clean = re.sub(r"[^A-Za-z0-9_-]+", "-", raw).strip("-")
	return f"{prefix}-{clean}"[:140]


def _ensure_item(record: Mapping[str, Any], prefix: str = "CC") -> tuple[str | None, bool]:
	code = _item_code(prefix, record)
	if frappe.db.exists("Item", code):
		return code, False
	item_group = _first_leaf("Item Group", "is_group")
	stock_uom = frappe.db.get_value("UOM", "Nos", "name") or _first_leaf("UOM")
	if not item_group or not stock_uom:
		return None, False
	doc = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": code,
			"item_name": str(record.get("name") or record.get("title") or code),
			"description": str(record.get("description") or record.get("notes") or ""),
			"item_group": item_group,
			"stock_uom": stock_uom,
			"is_stock_item": 1,
			"is_purchase_item": 1,
			"is_sales_item": 0,
		}
	).insert(ignore_permissions=True)
	return doc.name, True


def _ensure_contract(
	record: Mapping[str, Any], project: str | None, supplier: str | None
) -> tuple[str | None, bool]:
	if not supplier:
		return None, False
	contract_number = str(record.get("contractNumber") or record.get("id") or "").strip()
	if contract_number:
		existing = frappe.db.get_value(
			"Contract", {"party_type": "Supplier", "party_name": supplier, "signee": contract_number}, "name"
		)
		if existing:
			return existing, False
	terms = {
		"scope": record.get("projectScope"),
		"project_value_hnl": record.get("projectValueHnl"),
		"labor_value_hnl": record.get("laborValueHnl"),
		"payment_terms": record.get("paymentTerms"),
		"materials_included": record.get("materialsIncluded"),
		"materials_not_included": record.get("materialsNotIncluded"),
		"owner_obligations": record.get("ownerObligations"),
		"contractor_obligations": record.get("contractorObligations"),
		"change_order_terms": record.get("changeOrderTerms"),
		"source_record": record,
	}
	doc = frappe.get_doc(
		{
			"doctype": "Contract",
			"party_type": "Supplier",
			"party_name": supplier,
			"status": "Unsigned" if record.get("status") == "draft" else "Active",
			"start_date": _date(record.get("startDate")),
			"end_date": _date(record.get("targetEndDate")),
			"signee": contract_number or None,
			"contract_terms": f"<pre>{escape_html(_json(terms))}</pre>",
			"document_type": "Project" if project else None,
			"document_name": project,
		}
	).insert(ignore_permissions=True)
	return doc.name, True


def _upsert_custom(doctype: str, key: str, values: dict[str, Any]) -> tuple[str, bool]:
	if frappe.db.exists(doctype, key):
		doc = frappe.get_doc(doctype, key)
		doc.update(values)
		doc.save(ignore_permissions=True)
		return doc.name, False
	doc = frappe.get_doc({"doctype": doctype, "source_key": key, **values}).insert(ignore_permissions=True)
	return doc.name, True


def _preserve_legacy(
	run_name: str,
	project_key: str,
	entity_type: str,
	index: int,
	record: Mapping[str, Any],
) -> tuple[Any, bool, int]:
	source_id = project_key if entity_type in {"settings", "snapshot"} else source_record_id(record, index)
	payload_hash = sha256_json(record)
	key = versioned_record_key(project_key, entity_type, source_id, payload_hash)
	if frappe.db.exists("ConstruControl Legacy Record", key):
		return frappe.get_doc("ConstruControl Legacy Record", key), False, 0
	cleaned, redacted = sanitize_payload(record)
	doc = frappe.get_doc(
		{
			"doctype": "ConstruControl Legacy Record",
			"record_key": key,
			"migration_run": run_name,
			"project_key": project_key,
			"entity_type": entity_type,
			"source_id": source_id,
			"payload_hash": payload_hash,
			"migration_status": "Preserved",
			"source_created_at": _datetime(record.get("createdAt")),
			"source_updated_at": _datetime(record.get("updatedAt")),
			"is_deleted": _deleted(record),
			"raw_payload": _json(cleaned),
		}
	).insert(ignore_permissions=True)
	return doc, True, redacted


def _walk_evidence(value: Any) -> list[Mapping[str, Any]]:
	result: list[Mapping[str, Any]] = []
	if isinstance(value, list):
		for item in value:
			result.extend(_walk_evidence(item))
	elif isinstance(value, Mapping):
		if (value.get("dataUrl") or value.get("storagePath") or value.get("storageUrl")) and (
			value.get("name") or value.get("id")
		):
			result.append(value)
		for item in value.values():
			result.extend(_walk_evidence(item))
	return result


def _load_storage_export(source_path: Path, expected_files: int) -> tuple[dict[tuple[str, str], Path], dict[str, Any]]:
	manifest_path = source_path.parent / "storage-manifest.json"
	report: dict[str, Any] = {
		"expected_references": expected_files,
		"manifest": str(manifest_path),
		"available_files": 0,
		"errors": [],
	}
	if not manifest_path.is_file():
		if expected_files:
			report["errors"].append("storage-manifest.json is missing next to the source export")
		return {}, report
	try:
		items = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
	except Exception as exc:
		report["errors"].append(f"invalid storage manifest: {exc}")
		return {}, report
	if not isinstance(items, list):
		report["errors"].append("storage manifest must be a JSON array")
		return {}, report
	files: dict[tuple[str, str], Path] = {}
	base = source_path.parent.resolve()
	for index, item in enumerate(items):
		if not isinstance(item, Mapping):
			report["errors"].append(f"manifest row {index + 1} is not an object")
			continue
		bucket = str(item.get("bucket") or "construction-evidence")
		storage_path = str(item.get("path") or "")
		if item.get("status") != "downloaded":
			report["errors"].append(f"Storage object was not downloaded: {bucket}/{storage_path}")
			continue
		candidate = (base / str(item.get("exported_path") or "")).resolve()
		try:
			candidate.relative_to(base)
		except ValueError:
			report["errors"].append(f"Storage manifest path escapes the export directory: {candidate}")
			continue
		if not candidate.is_file():
			report["errors"].append(f"Exported Storage file is missing: {candidate}")
			continue
		content = candidate.read_bytes()
		if item.get("bytes") is not None and len(content) != cint(item.get("bytes")):
			report["errors"].append(f"Storage file size mismatch: {candidate}")
			continue
		if item.get("sha256") and hashlib.sha256(content).hexdigest() != item.get("sha256"):
			report["errors"].append(f"Storage file checksum mismatch: {candidate}")
			continue
		files[(bucket, storage_path)] = candidate
	report["available_files"] = len(files)
	return files, report


def _attach_evidence(
	record: Mapping[str, Any],
	doctype: str,
	name: str,
	storage_files: Mapping[tuple[str, str], Path],
) -> tuple[int, int]:
	created = 0
	rejected = 0
	seen: set[str] = set()
	for item in _walk_evidence(record):
		identifier = str(item.get("id") or item.get("storagePath") or item.get("name"))
		if identifier in seen:
			continue
		seen.add(identifier)
		try:
			data_url = item.get("dataUrl")
			if isinstance(data_url, str) and data_url.startswith("data:"):
				header, encoded = data_url.split(",", 1)
				content = base64.b64decode(encoded, validate=";base64" in header)
			else:
				bucket = str(item.get("storageBucket") or "construction-evidence")
				storage_path = str(item.get("storagePath") or "")
				exported = storage_files.get((bucket, storage_path))
				if not exported:
					raise ValueError("referenced Storage object is unavailable in the verified export")
				content = exported.read_bytes()
			if len(content) > MAX_EVIDENCE_BYTES:
				raise ValueError("evidence exceeds 12 MiB")
			file_name = str(item.get("name") or f"evidence-{identifier}").replace("/", "-").replace("\\", "-")
			existing = frappe.db.get_value(
				"File",
				{"attached_to_doctype": doctype, "attached_to_name": name, "file_name": file_name},
				"name",
			)
			if not existing:
				save_file(file_name, content, doctype, name, is_private=1)
				created += 1
		except Exception:
			rejected += 1
	return created, rejected


def _map_entity(
	project_key: str,
	entity_type: str,
	record: Mapping[str, Any],
	legacy: Any,
	context: dict[str, Any],
	settings: Any,
) -> tuple[str | None, str | None, bool, int, int]:
	source_id = legacy.source_id
	stable_key = source_key(project_key, entity_type, source_id)
	project = context.get("project")
	phase = context.get("phases", {}).get(str(record.get("phaseId")))
	target_doctype: str | None = None
	target_name: str | None = None
	created = False

	if entity_type == "settings":
		target_doctype, target_name, created = "Project", context.get("project"), context.get("project_created", False)
	elif entity_type == "phases":
		target_name, created = _ensure_task(project, record, context.get("company"))
		target_doctype = "Task" if target_name else None
		if target_name:
			context.setdefault("phases", {})[source_id] = target_name
	elif entity_type == "incomes":
		values = {
			"source_id": source_id,
			"legacy_record": legacy.name,
			"project": project,
			"title": record.get("title") or source_id,
			"income_type": record.get("type") or "other",
			"status": record.get("status") or "pending",
			"date_sent": _date(record.get("dateSent")),
			"date_received": _date(record.get("dateReceived")) or getdate(),
			"currency": record.get("currency") or "HNL",
			"original_amount": flt(record.get("originalAmount")),
			"exchange_rate": flt(record.get("exchangeRate")) or 1,
			"amount_hnl": flt(record.get("amountHnl")),
			"sender": record.get("sender"),
			"origin_country": record.get("originCountry"),
			"remittance_company": record.get("remittanceCompany"),
			"bank": record.get("bank"),
			"reference": record.get("reference"),
			"notes": record.get("notes"),
			"evidence_manifest_json": _json(evidence_manifest(record)),
			"is_logically_deleted": _deleted(record),
		}
		target_doctype = "ConstruControl Fund Entry"
		target_name, created = _upsert_custom(target_doctype, stable_key, values)
		context.setdefault("incomes", {})[source_id] = target_name
	elif entity_type == "expenses":
		supplier = None
		if settings.migration_mode == STANDARD_MODE:
			supplier, _ = _ensure_supplier(record.get("providerName"))
		values = {
			"source_id": source_id,
			"legacy_record": legacy.name,
			"project": project,
			"phase_task": phase,
			"title": record.get("title") or source_id,
			"description": record.get("description") or record.get("title") or source_id,
			"posting_date": _date(record.get("date")) or getdate(),
			"category": record.get("category") or "other",
			"subcategory": record.get("subcategory"),
			"status": record.get("status") or "pending",
			"financial_status": record.get("financialStatus"),
			"document_status": record.get("documentStatus"),
			"approval_status": record.get("approvalStatus"),
			"provider_name": record.get("providerName") or "Unknown legacy provider",
			"supplier": supplier,
			"payment_method": record.get("paymentMethod"),
			"amount_hnl": flt(record.get("amountHnl")),
			"fund_entry": context.get("incomes", {}).get(str(record.get("paymentSourceId"))),
			"labor_contract": context.get("contracts", {}).get(str(record.get("laborContractId"))),
			"labor_payment_type": record.get("laborPaymentType"),
			"folio": record.get("folio"),
			"document_json": _json(record.get("document") or {}),
			"evidence_manifest_json": _json(evidence_manifest(record)),
			"notes": record.get("notes"),
			"is_logically_deleted": _deleted(record),
		}
		target_doctype = "ConstruControl Expense Record"
		target_name, created = _upsert_custom(target_doctype, stable_key, values)
		context.setdefault("expenses", {})[source_id] = target_name
	elif entity_type == "progressUpdates":
		values = {
			"source_id": source_id,
			"legacy_record": legacy.name,
			"project": project,
			"task": phase,
			"update_date": _date(record.get("date")) or getdate(),
			"title": record.get("title") or source_id,
			"description": record.get("description"),
			"progress_percent": flt(record.get("progressPercent")),
			"moment": record.get("moment"),
			"quality": record.get("quality"),
			"responsible": record.get("responsible"),
			"location": record.get("location"),
			"tags": ", ".join(record.get("tags") or []),
			"evidence_manifest_json": _json(evidence_manifest(record)),
			"is_logically_deleted": _deleted(record),
		}
		target_doctype = "ConstruControl Progress Update"
		target_name, created = _upsert_custom(target_doctype, stable_key, values)
	elif entity_type == "weeklyClosings":
		snapshot = record.get("snapshot") if isinstance(record.get("snapshot"), Mapping) else {}
		values = {
			"source_id": source_id,
			"legacy_record": legacy.name,
			"project": project,
			"title": record.get("title") or source_id,
			"week_start": _date(record.get("weekStart")) or getdate(),
			"week_end": _date(record.get("weekEnd")) or getdate(),
			"status": record.get("status") or "draft",
			"initial_balance_hnl": flt(snapshot.get("initialBalanceHnl")),
			"income_hnl": flt(snapshot.get("incomeHnl")),
			"expense_hnl": flt(snapshot.get("expenseHnl")),
			"final_balance_hnl": flt(snapshot.get("finalBalanceHnl")),
			"pending_expense_hnl": flt(snapshot.get("pendingExpenseHnl")),
			"missing_receipt_hnl": flt(snapshot.get("missingReceiptHnl")),
			"snapshot_json": _json(snapshot),
			"pending_items_json": _json(record.get("pendingItems") or []),
			"evidence_manifest_json": _json(evidence_manifest(record)),
			"notes": record.get("notes"),
			"is_logically_deleted": _deleted(record),
		}
		target_doctype = "ConstruControl Weekly Closing"
		target_name, created = _upsert_custom(target_doctype, stable_key, values)
	elif entity_type == "changeOrders":
		values = {
			"source_id": source_id,
			"legacy_record": legacy.name,
			"project": project,
			"task": phase,
			"contract": context.get("contracts", {}).get(str(record.get("contractId"))),
			"change_order_code": record.get("code"),
			"title": record.get("title") or source_id,
			"status": record.get("status") or "draft",
			"reason": record.get("reason"),
			"description": record.get("description"),
			"cost_impact_hnl": flt(record.get("costImpactHnl")),
			"schedule_impact_days": cint(record.get("scheduleImpactDays")),
			"requested_by_name": record.get("requestedBy"),
			"approved_by_name": record.get("approvedBy"),
			"requested_at": _datetime(record.get("requestedAt")),
			"decided_at": _datetime(record.get("decidedAt")),
		}
		target_doctype = "ConstruControl Change Order"
		target_name, created = _upsert_custom(target_doctype, stable_key, values)
	elif entity_type == "approvalRequests":
		values = {
			"source_id": source_id,
			"legacy_record": legacy.name,
			"project": project,
			"approval_code": record.get("code"),
			"title": record.get("title") or source_id,
			"category": record.get("category"),
			"priority": record.get("priority"),
			"status": record.get("status") or "pending",
			"amount_hnl": flt(record.get("amountHnl")),
			"requester": record.get("requester"),
			"approver": record.get("approver"),
			"due_date": _date(record.get("dueDate")),
			"reference": record.get("reference"),
			"decision_note": record.get("decisionNote"),
			"comments_json": _json(record.get("comments") or []),
			"decided_at": _datetime(record.get("decidedAt")),
		}
		target_doctype = "ConstruControl Approval"
		target_name, created = _upsert_custom(target_doctype, stable_key, values)
	elif entity_type in {"auditLogs", "enterprisePlatform.immutableAudit"}:
		raw_hash = str(record.get("eventHash") or record.get("hash") or sha256_json(record))
		event_key = hashlib.sha256(f"{project_key}|{source_id}|{raw_hash}".encode()).hexdigest()[:40]
		target_doctype = "ConstruControl Audit Event"
		if frappe.db.exists(target_doctype, event_key):
			target_name, created = event_key, False
		else:
			target_name = frappe.get_doc(
				{
					"doctype": target_doctype,
					"event_key": event_key,
					"source_id": source_id,
					"legacy_record": legacy.name,
					"project": project,
					"event_at": _datetime(record.get("createdAt") or record.get("eventAt")) or now_datetime(),
					"actor": record.get("actor") or record.get("createdBy"),
					"actor_role": record.get("actorRole"),
					"action": record.get("action") or record.get("eventType") or "legacy_event",
					"record_type": record.get("recordType"),
					"record_id": record.get("recordId"),
					"title": record.get("title"),
					"description": record.get("description"),
					"previous_state": record.get("previousState"),
					"next_state": record.get("nextState"),
					"reason": record.get("reason"),
					"event_hash": raw_hash,
					"previous_hash": record.get("previousHash"),
					"raw_event_json": _json(record),
				}
			).insert(ignore_permissions=True).name
			created = True
	elif entity_type == "laborContracts" and settings.migration_mode == STANDARD_MODE:
		party = record.get("contractorParty") if isinstance(record.get("contractorParty"), Mapping) else record
		supplier, supplier_created = _ensure_supplier(record.get("contractorName"), party)
		target_name, contract_created = _ensure_contract(record, project, supplier)
		target_doctype = "Contract" if target_name else None
		created = supplier_created or contract_created
		if target_name:
			context.setdefault("contracts", {})[source_id] = target_name
	elif entity_type == "materials" and settings.migration_mode == STANDARD_MODE:
		target_name, created = _ensure_item(record)
		target_doctype = "Item" if target_name else None
		if target_name:
			context.setdefault("materials", {})[source_id] = target_name
	elif entity_type == "enterprisePlatform.partners" and settings.migration_mode == STANDARD_MODE:
		target_name, created = _ensure_supplier(record.get("name") or record.get("businessName"), record)
		target_doctype = "Supplier" if target_name else None
	elif entity_type == "enterprisePlatform.catalog" and settings.migration_mode == STANDARD_MODE:
		target_name, created = _ensure_item(record, "CC-CAT")
		target_doctype = "Item" if target_name else None
	elif entity_type == "userAccounts" and settings.allow_user_creation:
		email = str(record.get("email") or "").strip().lower()
		if email and "@" in email:
			target_doctype = "User"
			if frappe.db.exists("User", email):
				target_name, created = email, False
			else:
				user = frappe.get_doc(
					{
						"doctype": "User",
						"email": email,
						"first_name": record.get("name") or email.split("@", 1)[0],
						"enabled": cint(record.get("status") == "active"),
						"send_welcome_email": 0,
						"user_type": "System User",
					}
				).insert(ignore_permissions=True)
				role = ROLE_MAP.get(str(record.get("role")), "ConstruControl Viewer")
				user.add_roles(role)
				target_name, created = user.name, True

	return target_doctype, target_name, created, 0, 0


def run_import(
	source_path: str,
	dry_run: bool = True,
	source_kind: str = "ConstruControl Backup",
	backup_reference: str | None = None,
) -> dict[str, Any]:
	"""Validate and import a ConstruControl JSON export through a repeatable Frappe transaction."""
	path = Path(source_path).expanduser().resolve()
	if not path.is_file():
		frappe.throw(_("Source file does not exist: {0}").format(path))
	if not dry_run and not backup_reference:
		frappe.throw(_("A bench backup reference is required before a real migration."))
	raw = path.read_bytes()
	file_hash = hashlib.sha256(raw).hexdigest()
	payload = json.loads(raw.decode("utf-8-sig"))
	projects = normalize_export_document(payload)
	reports = [preflight_snapshot(project.snapshot) for project in projects]
	expected_storage_files = sum(cint(report.get("counts", {}).get("storage_evidence_files")) for report in reports)
	storage_files, storage_report = _load_storage_export(path, expected_storage_files)
	if not dry_run and storage_report["errors"]:
		frappe.throw(
			_("The verified Storage export is incomplete; run a dry run and correct its manifest before importing."),
			title=_("Incomplete evidence export"),
		)

	if not dry_run:
		existing = frappe.db.get_value(
			"ConstruControl Migration Run",
			{"source_sha256": file_hash, "dry_run": 0, "status": ["in", ["Completed", "Completed with Warnings"]]},
			"name",
			order_by="creation desc",
		)
		if existing:
			return {"migration_run": existing, "idempotent_reuse": True, "source_sha256": file_hash}

	run = frappe.get_doc(
		{
			"doctype": "ConstruControl Migration Run",
			"naming_series": "CC-MIG-.YYYY.-.#####",
			"status": "Validating" if dry_run else "Running",
			"dry_run": cint(dry_run),
			"source_kind": source_kind,
			"source_sha256": file_hash,
			"started_at": now_datetime(),
			"backup_reference": backup_reference,
			"rollback_status": "Not Requested" if dry_run else "Ready",
			"input_counts_json": _json(aggregate_counts(reports)),
			"validation_report_json": _json(
				{
					"storage_export": storage_report,
					"projects": [
						{"project_key": project.project_key, "report": report}
						for project, report in zip(projects, reports, strict=True)
					]
				}
			),
		}
	).insert(ignore_permissions=True)

	output: Counter[str] = Counter()
	output["storage_export_errors"] = len(storage_report["errors"])
	output["storage_files_verified"] = cint(storage_report["available_files"])
	errors: list[str] = []
	if not dry_run:
		settings = _settings_doc()
		for project in projects:
			project_name, project_created = _ensure_project(project.project_key, project.snapshot, settings)
			context = {
				"project": project_name,
				"project_created": project_created,
				"company": _company(settings),
				"phases": {},
				"incomes": {},
				"contracts": {},
				"materials": {},
			}
			# Preserve the complete snapshot first, including unknown collections.
			_, created, redacted = _preserve_legacy(
				run.name, project.project_key, "snapshot", 0, project.snapshot
			)
			output["legacy_records_created"] += cint(created)
			output["legacy_records_reused"] += cint(not created)
			output["sensitive_fields_redacted"] += redacted
			output["preserved.snapshot"] += 1
			for entity_type, index, record in iter_entities(project.snapshot):
				legacy, legacy_created, redacted = _preserve_legacy(
					run.name, project.project_key, entity_type, index, record
				)
				output["legacy_records_created"] += cint(legacy_created)
				output["legacy_records_reused"] += cint(not legacy_created)
				output["sensitive_fields_redacted"] += redacted
				output[f"preserved.{entity_type}"] += 1
				if not legacy_created and legacy.target_name:
					output["identical_records_skipped"] += 1
					continue
				try:
					target_doctype, target_name, target_created, _, _ = _map_entity(
						project.project_key, entity_type, record, legacy, context, settings
					)
					if target_doctype and target_name:
						legacy.db_set(
							{
								"migration_status": "Mapped",
								"target_doctype": target_doctype,
								"target_name": target_name,
								"created_by_migration": cint(target_created),
							},
							update_modified=False,
						)
						output["records_mapped"] += 1
						output["targets_created"] += cint(target_created)
						output["targets_reused_or_updated"] += cint(not target_created)
					else:
						output["records_preserved_only"] += 1
					attachment_doctype = target_doctype or "ConstruControl Legacy Record"
					attachment_name = target_name or legacy.name
					attachments, rejected = _attach_evidence(
						record, attachment_doctype, attachment_name, storage_files
					)
					output["attachments_created"] += attachments
					output["attachments_rejected"] += rejected
				except Exception as exc:
					message = f"{project.project_key}/{entity_type}/{legacy.source_id}: {exc}"
					legacy.db_set(
						{"migration_status": "Failed", "error_detail": message}, update_modified=False
					)
					errors.append(message)
					output["mapping_failures"] += 1

	preflight_errors = sum(report["error_count"] for report in reports)
	preflight_warnings = sum(report["warning_count"] for report in reports)
	output["preflight_errors"] = preflight_errors
	output["preflight_warnings"] = preflight_warnings
	run.status = (
		"Completed with Warnings"
		if preflight_errors or preflight_warnings or storage_report["errors"] or errors
		else "Completed"
	)
	run.completed_at = now_datetime()
	run.output_counts_json = _json(dict(sorted(output.items())))
	run.error_log = "\n".join(errors)
	run.save(ignore_permissions=True)
	return {
		"migration_run": run.name,
		"dry_run": bool(dry_run),
		"source_sha256": file_hash,
		"input_counts": aggregate_counts(reports),
		"output_counts": dict(sorted(output.items())),
		"status": run.status,
	}


def rollback(migration_run: str) -> dict[str, Any]:
	"""Delete only draft targets created by one migration; append-only audit events remain."""
	run = frappe.get_doc("ConstruControl Migration Run", migration_run)
	if run.dry_run:
		frappe.throw(_("A dry run has no data to roll back."))
	if run.status == "Rolled Back":
		return {"migration_run": run.name, "idempotent_reuse": True, "status": run.status}
	run.db_set("rollback_status", "Running", update_modified=False)
	records = frappe.get_all(
		"ConstruControl Legacy Record",
		filters={"migration_run": run.name},
		fields=["name", "target_doctype", "target_name", "created_by_migration"],
		order_by="creation desc",
		limit_page_length=0,
	)
	counts: Counter[str] = Counter()
	errors: list[str] = []
	for record in records:
		try:
			if record.created_by_migration and record.target_doctype and record.target_name:
				if record.target_doctype == "ConstruControl Audit Event":
					counts["audit_events_retained"] += 1
				elif frappe.db.exists(record.target_doctype, record.target_name):
					other_links = frappe.db.count(
						"ConstruControl Legacy Record",
						{
							"target_doctype": record.target_doctype,
							"target_name": record.target_name,
							"migration_run": ["!=", run.name],
						},
					)
					docstatus = cint(frappe.db.get_value(record.target_doctype, record.target_name, "docstatus"))
					if not other_links and docstatus == 0:
						frappe.delete_doc(record.target_doctype, record.target_name, ignore_permissions=True)
						counts["targets_deleted"] += 1
					else:
						counts["targets_retained"] += 1
			frappe.delete_doc("ConstruControl Legacy Record", record.name, ignore_permissions=True)
			counts["legacy_records_deleted"] += 1
		except Exception as exc:
			errors.append(f"{record.name}: {exc}")
			counts["rollback_failures"] += 1
	run.rollback_status = "Failed" if errors else "Completed"
	if not errors:
		run.status = "Rolled Back"
	run.error_log = "\n".join(filter(None, [run.error_log, *errors]))
	run.save(ignore_permissions=True)
	return {
		"migration_run": run.name,
		"status": run.status,
		"rollback_status": run.rollback_status,
		"counts": dict(sorted(counts.items())),
		"errors": errors,
	}
