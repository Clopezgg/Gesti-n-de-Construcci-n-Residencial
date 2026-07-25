from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from nexora.directory.common import _entity_snapshot, _lock, _reference_counts, _resolve_chain
from nexora.directory.core import assert_no_consolidation_cycle
from nexora.financial.context import service_write
from nexora.financial.core import canonical_payload_hash
from nexora.financial.db import (
	audit,
	complete_idempotency,
	correlation,
	issue_document_number,
	link_sequence,
	rollback,
	savepoint,
	start_idempotency,
)
from nexora.permissions import require_action


def consolidate_entities(source: str, target: str, reason: str, idempotency_key: str) -> dict[str, Any]:
	require_action("consolidate_entity")
	if not str(reason or "").strip():
		frappe.throw(_("La consolidación requiere motivo."))
	payload = {"source": source, "target": target, "reason": reason}
	payload_hash = canonical_payload_hash(payload)
	correlation_id = correlation(payload)
	point = savepoint()
	try:
		idem, cached = start_idempotency(idempotency_key, payload_hash, correlation_id)
		if cached is not None:
			return cached
		locked = {name: _lock("NXR Entity", name) for name in sorted({source, target})}
		source_doc = locked[source]
		target_doc = locked[target]
		if source_doc.status not in {"Active", "Blocked"} or target_doc.status not in {"Active", "Blocked"}:
			frappe.throw(_("Origen y destino deben estar activos o bloqueados."))
		merged_map = {
			row.name: row.merged_into
			for row in frappe.db.get_all("NXR Entity", fields=["name", "merged_into"])
		}
		try:
			assert_no_consolidation_cycle(source, target, merged_map)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		before_counts = _reference_counts(source)
		snapshot_hash = canonical_payload_hash(_entity_snapshot(source_doc, include_sensitive=True))
		number, sequence = issue_document_number("NXR Entity Consolidation", idempotency_key)
		with service_write():
			consolidation = frappe.get_doc(
				{
					"doctype": "NXR Entity Consolidation",
					"document_number": number,
					"source_entity": source,
					"target_entity": target,
					"reason": reason,
					"source_snapshot_hash": snapshot_hash,
					"consolidated_by": frappe.session.user,
					"consolidated_at": frappe.utils.now_datetime(),
					"idempotency_key": idempotency_key,
					"payload_hash": payload_hash,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
			source_doc.status = "Consolidated"
			source_doc.merged_into = target
			source_doc.consolidation_record = consolidation.name
			source_doc.save(ignore_permissions=True)
		link_sequence(sequence, consolidation.name)
		after_counts = _reference_counts(source)
		if before_counts != after_counts:
			frappe.throw(_("La consolidación alteró referencias del expediente de origen."))
		result = {
			"consolidation": consolidation.name,
			"document_number": number,
			"source": source,
			"target": target,
			"source_snapshot_hash": snapshot_hash,
			"preserved_references": after_counts,
		}
		audit(
			"entities_consolidated",
			"NXR Entity Consolidation",
			consolidation.name,
			payload_hash,
			correlation_id,
			result,
		)
		complete_idempotency(idem, "NXR Entity Consolidation", consolidation.name, result)
		return result
	except Exception:
		rollback(point)
		raise


def resolve_canonical_entity(entity: str) -> dict[str, Any]:
	require_action("read_entities")
	canonical, chain = _resolve_chain(entity)
	return {"requested": entity, "canonical": canonical, "chain": chain}
