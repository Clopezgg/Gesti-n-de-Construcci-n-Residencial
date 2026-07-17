from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from typing import Any


CORE_COLLECTIONS = (
	"phases",
	"incomes",
	"expenses",
	"laborContracts",
	"materials",
	"inventoryMovements",
	"progressUpdates",
	"weeklyClosings",
	"reports",
	"notificationContacts",
	"notificationRules",
	"notificationLogs",
	"auditLogs",
	"userAccounts",
	"procurementRequests",
	"equipmentRecords",
	"changeOrders",
	"approvalRequests",
)

ENTERPRISE_COLLECTIONS = (
	"projects",
	"permissionOverrides",
	"partners",
	"catalog",
	"payables",
	"documentTemplates",
	"automationRules",
	"automationExecutions",
	"dailyLogs",
	"crewMembers",
	"crewAttendance",
	"tools",
	"toolLoans",
	"safetyIncidents",
	"signatures",
	"immutableAudit",
	"backupHistory",
)

SENSITIVE_KEYS = {
	"password",
	"passwordHash",
	"pinHash",
	"access_token",
	"refresh_token",
	"service_role",
	"service_role_key",
	"supabase_service_role_key",
}


@dataclass(frozen=True)
class SourceProject:
	project_key: str
	snapshot: dict[str, Any]


def canonical_json(value: Any) -> str:
	return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_json(value: Any) -> str:
	return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def source_record_id(record: Mapping[str, Any], index: int) -> str:
	value = record.get("id") or record.get("code") or record.get("name")
	return str(value).strip() if value else f"missing-id-{index + 1}-{sha256_json(record)[:12]}"


def source_key(project_key: str, entity_type: str, source_id: str) -> str:
	value = f"{project_key}|{entity_type}|{source_id}"
	return hashlib.sha256(value.encode("utf-8")).hexdigest()[:40]


def versioned_record_key(project_key: str, entity_type: str, source_id: str, payload_hash: str) -> str:
	value = f"{project_key}|{entity_type}|{source_id}|{payload_hash}"
	return hashlib.sha256(value.encode("utf-8")).hexdigest()[:40]


def sanitize_payload(value: Any) -> tuple[Any, int]:
	"""Remove authentication material while retaining a count for reconciliation."""
	if isinstance(value, list):
		items = []
		redacted = 0
		for item in value:
			clean, count = sanitize_payload(item)
			items.append(clean)
			redacted += count
		return items, redacted
	if not isinstance(value, Mapping):
		return value, 0
	cleaned: dict[str, Any] = {}
	redacted = 0
	for key, item in value.items():
		if key in SENSITIVE_KEYS or key.lower() in {entry.lower() for entry in SENSITIVE_KEYS}:
			redacted += 1
			continue
		clean, count = sanitize_payload(item)
		cleaned[str(key)] = clean
		redacted += count
	return cleaned, redacted


def _is_snapshot(value: Any) -> bool:
	return isinstance(value, Mapping) and isinstance(value.get("settings"), Mapping)


def _row_to_project(row: Mapping[str, Any], index: int) -> SourceProject:
	candidate = row.get("data") if _is_snapshot(row.get("data")) else row
	if not _is_snapshot(candidate):
		raise ValueError(f"Project row {index + 1} does not contain a ConstruControl AppData snapshot.")
	settings = candidate.get("settings", {})
	project_key = str(
		row.get("project_id")
		or row.get("projectId")
		or settings.get("cloudProjectId")
		or settings.get("activeProjectId")
		or settings.get("projectName")
		or f"project-{index + 1}"
	).strip()
	return SourceProject(project_key=project_key, snapshot=dict(candidate))


def normalize_export_document(payload: Any) -> list[SourceProject]:
	"""Accept native backups, localStorage exports, and Supabase REST/SQL exports."""
	if _is_snapshot(payload):
		return [_row_to_project(payload, 0)]
	if isinstance(payload, Mapping) and _is_snapshot(payload.get("data")):
		return [_row_to_project(payload, 0)]
	rows: Any = payload
	if isinstance(payload, Mapping):
		for key in ("rows", "construction_projects", "projects"):
			if isinstance(payload.get(key), list):
				rows = payload[key]
				break
	if not isinstance(rows, list) or not rows:
		raise ValueError("The file contains no ConstruControl project snapshots.")
	projects = []
	for index, row in enumerate(rows):
		if not isinstance(row, Mapping):
			raise ValueError(f"Project row {index + 1} is not an object.")
		projects.append(_row_to_project(row, index))
	keys = [item.project_key for item in projects]
	if len(keys) != len(set(keys)):
		raise ValueError("The export repeats a project key; split or correct the source export before importing.")
	return projects


def iter_entities(snapshot: Mapping[str, Any]) -> Iterator[tuple[str, int, dict[str, Any]]]:
	settings = snapshot.get("settings")
	if isinstance(settings, Mapping):
		yield "settings", 0, dict(settings)
	for collection in CORE_COLLECTIONS:
		items = snapshot.get(collection, [])
		if not isinstance(items, list):
			continue
		for index, item in enumerate(items):
			if isinstance(item, Mapping):
				yield collection, index, dict(item)
	enterprise = snapshot.get("enterprisePlatform")
	if isinstance(enterprise, Mapping):
		for collection in ENTERPRISE_COLLECTIONS:
			items = enterprise.get(collection, [])
			if not isinstance(items, list):
				continue
			for index, item in enumerate(items):
				if isinstance(item, Mapping):
					yield f"enterprisePlatform.{collection}", index, dict(item)


def _collection_ids(snapshot: Mapping[str, Any], name: str) -> set[str]:
	items = snapshot.get(name, [])
	if not isinstance(items, list):
		return set()
	return {str(item.get("id")) for item in items if isinstance(item, Mapping) and item.get("id")}


def _evidence_items(value: Any) -> Iterator[Mapping[str, Any]]:
	if isinstance(value, list):
		for item in value:
			yield from _evidence_items(item)
	elif isinstance(value, Mapping):
		if ("dataUrl" in value or "storagePath" in value or "storageUrl" in value) and (
			"name" in value or "id" in value
		):
			yield value
		for item in value.values():
			yield from _evidence_items(item)


def evidence_manifest(record: Mapping[str, Any]) -> list[dict[str, Any]]:
	manifest = []
	seen: set[str] = set()
	for item in _evidence_items(record):
		key = str(item.get("id") or item.get("storagePath") or item.get("storageUrl") or item.get("name"))
		if key in seen:
			continue
		seen.add(key)
		manifest.append(
			{
				"id": item.get("id"),
				"name": item.get("name"),
				"type": item.get("type"),
				"size": item.get("size"),
				"uploadedAt": item.get("uploadedAt"),
				"storageBucket": item.get("storageBucket"),
				"storagePath": item.get("storagePath"),
				"storageUrl": item.get("storageUrl"),
				"hasEmbeddedData": bool(item.get("dataUrl")),
			}
		)
	return manifest


def _duplicates(items: Any) -> list[str]:
	if not isinstance(items, list):
		return []
	ids = [str(item.get("id")) for item in items if isinstance(item, Mapping) and item.get("id")]
	return sorted(value for value, count in Counter(ids).items() if count > 1)


def _orphan(
	issues: list[dict[str, str]],
	entity: str,
	record: Mapping[str, Any],
	field: str,
	valid_ids: set[str],
	target: str,
) -> None:
	value = record.get(field)
	if value and str(value) not in valid_ids:
		issues.append(
			{
				"severity": "error",
				"code": "orphan_reference",
				"entity": entity,
				"source_id": str(record.get("id") or ""),
				"field": field,
				"value": str(value),
				"target_collection": target,
			}
		)


def preflight_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
	issues: list[dict[str, str]] = []
	counts: dict[str, int] = {"settings": 1 if isinstance(snapshot.get("settings"), Mapping) else 0}
	missing_ids: dict[str, int] = {}
	duplicates: dict[str, list[str]] = {}

	for collection in CORE_COLLECTIONS:
		items = snapshot.get(collection, [])
		if not isinstance(items, list):
			issues.append({"severity": "error", "code": "invalid_collection", "entity": collection})
			counts[collection] = 0
			continue
		counts[collection] = len(items)
		missing = sum(1 for item in items if not isinstance(item, Mapping) or not item.get("id"))
		if missing:
			missing_ids[collection] = missing
		duplicates_for_collection = _duplicates(items)
		if duplicates_for_collection:
			duplicates[collection] = duplicates_for_collection

	enterprise = snapshot.get("enterprisePlatform")
	if enterprise is not None and not isinstance(enterprise, Mapping):
		issues.append({"severity": "error", "code": "invalid_enterprise_platform", "entity": "enterprisePlatform"})
	elif isinstance(enterprise, Mapping):
		for collection in ENTERPRISE_COLLECTIONS:
			items = enterprise.get(collection, [])
			key = f"enterprisePlatform.{collection}"
			if not isinstance(items, list):
				issues.append({"severity": "error", "code": "invalid_collection", "entity": key})
				counts[key] = 0
				continue
			counts[key] = len(items)
			missing = sum(1 for item in items if not isinstance(item, Mapping) or not item.get("id"))
			if missing:
				missing_ids[key] = missing
			duplicates_for_collection = _duplicates(items)
			if duplicates_for_collection:
				duplicates[key] = duplicates_for_collection

	phase_ids = _collection_ids(snapshot, "phases")
	income_ids = _collection_ids(snapshot, "incomes")
	contract_ids = _collection_ids(snapshot, "laborContracts")
	material_ids = _collection_ids(snapshot, "materials")
	expense_ids = _collection_ids(snapshot, "expenses")

	for record in snapshot.get("expenses", []) if isinstance(snapshot.get("expenses"), list) else []:
		if isinstance(record, Mapping):
			_orphan(issues, "expenses", record, "phaseId", phase_ids, "phases")
			_orphan(issues, "expenses", record, "paymentSourceId", income_ids, "incomes")
			_orphan(issues, "expenses", record, "laborContractId", contract_ids, "laborContracts")
	for record in snapshot.get("laborContracts", []) if isinstance(snapshot.get("laborContracts"), list) else []:
		if isinstance(record, Mapping):
			_orphan(issues, "laborContracts", record, "phaseId", phase_ids, "phases")
	for record in snapshot.get("materials", []) if isinstance(snapshot.get("materials"), list) else []:
		if isinstance(record, Mapping):
			_orphan(issues, "materials", record, "phaseId", phase_ids, "phases")
			_orphan(issues, "materials", record, "relatedExpenseId", expense_ids, "expenses")
	for collection in ("inventoryMovements", "progressUpdates", "procurementRequests"):
		for record in snapshot.get(collection, []) if isinstance(snapshot.get(collection), list) else []:
			if isinstance(record, Mapping):
				_orphan(issues, collection, record, "phaseId", phase_ids, "phases")
	for record in snapshot.get("inventoryMovements", []) if isinstance(snapshot.get("inventoryMovements"), list) else []:
		if isinstance(record, Mapping):
			_orphan(issues, "inventoryMovements", record, "materialId", material_ids, "materials")
	for record in snapshot.get("changeOrders", []) if isinstance(snapshot.get("changeOrders"), list) else []:
		if isinstance(record, Mapping):
			_orphan(issues, "changeOrders", record, "phaseId", phase_ids, "phases")
			_orphan(issues, "changeOrders", record, "contractId", contract_ids, "laborContracts")

	all_evidence = list(_evidence_items(snapshot))
	counts["evidence_files"] = len(all_evidence)
	counts["embedded_evidence_files"] = sum(1 for item in all_evidence if item.get("dataUrl"))
	counts["storage_evidence_files"] = sum(1 for item in all_evidence if item.get("storagePath"))
	_, redacted = sanitize_payload(snapshot)
	counts["redacted_sensitive_fields"] = redacted

	for collection, values in duplicates.items():
		issues.append(
			{
				"severity": "error",
				"code": "duplicate_source_id",
				"entity": collection,
				"values": ", ".join(values),
			}
		)
	for collection, count in missing_ids.items():
		issues.append(
			{
				"severity": "warning",
				"code": "missing_source_id",
				"entity": collection,
				"count": str(count),
			}
		)

	known_top_level = set(CORE_COLLECTIONS) | {"settings", "enterprisePlatform"}
	unknown = sorted(str(key) for key in snapshot if key not in known_top_level)
	if unknown:
		issues.append(
			{
				"severity": "warning",
				"code": "unknown_top_level_fields",
				"entity": "snapshot",
				"values": ", ".join(unknown),
			}
		)

	return {
		"counts": counts,
		"duplicates": duplicates,
		"missing_ids": missing_ids,
		"issues": issues,
		"error_count": sum(1 for issue in issues if issue.get("severity") == "error"),
		"warning_count": sum(1 for issue in issues if issue.get("severity") == "warning"),
	}


def aggregate_counts(reports: Iterable[Mapping[str, Any]]) -> dict[str, int]:
	total: Counter[str] = Counter()
	for report in reports:
		for key, value in report.get("counts", {}).items():
			total[str(key)] += int(value)
	return dict(sorted(total.items()))
