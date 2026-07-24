from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping

import frappe

from nexora.directory.common import _contact_rows, _identifier_rows, _resolve_chain
from nexora.directory.core import duplicate_score, normalize_name
from nexora.financial.db import parse_payload
from nexora.permissions import require_action


def detect_entity_duplicates(payload: str | Mapping[str, Any]) -> list[dict[str, Any]]:
	require_action("read_entities")
	data = parse_payload(payload)
	exclude = str(data.get("entity") or "").strip() or None
	if exclude:
		doc = frappe.get_doc("NXR Entity", exclude)
		name_key = doc.normalized_name
		identifier_hashes = {row.normalized_hash for row in doc.identifiers}
		contact_hashes = {row.normalized_hash for row in doc.contacts}
		linked_user = doc.linked_user
	else:
		name_key = normalize_name(data.get("display_name"))
		identifier_hashes = {row["normalized_hash"] for row in _identifier_rows(data.get("identifiers"))}
		contact_hashes = {row["normalized_hash"] for row in _contact_rows(data.get("contacts"))}
		linked_user = str(data.get("linked_user") or "").strip() or None
	candidate_ids: set[str] = set()
	identifier_counts: defaultdict[str, int] = defaultdict(int)
	contact_counts: defaultdict[str, int] = defaultdict(int)
	if identifier_hashes:
		for row in frappe.db.get_all(
			"NXR Entity Identifier",
			filters={"normalized_hash": ["in", list(identifier_hashes)]},
			fields=["parent"],
		):
			candidate_ids.add(row.parent)
			identifier_counts[row.parent] += 1
	if contact_hashes:
		for row in frappe.db.get_all(
			"NXR Entity Contact", filters={"normalized_hash": ["in", list(contact_hashes)]}, fields=["parent"]
		):
			candidate_ids.add(row.parent)
			contact_counts[row.parent] += 1
	if name_key:
		candidate_ids.update(
			row.name
			for row in frappe.db.get_all("NXR Entity", filters={"normalized_name": name_key}, fields=["name"])
		)
	if linked_user:
		candidate_ids.update(
			row.name
			for row in frappe.db.get_all("NXR Entity", filters={"linked_user": linked_user}, fields=["name"])
		)
	candidate_ids.discard(exclude)
	results: list[dict[str, Any]] = []
	for candidate in candidate_ids:
		row = frappe.db.get_value(
			"NXR Entity",
			candidate,
			[
				"name",
				"document_number",
				"status",
				"entity_type",
				"display_name",
				"normalized_name",
				"linked_user",
			],
			as_dict=True,
		)
		if not row:
			continue
		score, reasons = duplicate_score(
			name_matches=bool(name_key and row.normalized_name == name_key),
			identifier_matches=identifier_counts[candidate],
			contact_matches=contact_counts[candidate],
			linked_user_matches=bool(linked_user and row.linked_user == linked_user),
		)
		if score:
			canonical, chain = _resolve_chain(row.name)
			results.append(
				{
					"entity": row.name,
					"canonical_entity": canonical,
					"redirect_chain": chain,
					"document_number": row.document_number,
					"status": row.status,
					"entity_type": row.entity_type,
					"display_name": row.display_name,
					"score": score,
					"reasons": list(reasons),
				}
			)
	return sorted(results, key=lambda row: (-row["score"], row["display_name"]))[:50]
