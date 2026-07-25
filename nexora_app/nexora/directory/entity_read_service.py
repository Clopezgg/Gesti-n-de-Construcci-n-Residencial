from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from nexora.directory.common import (
	CONTACT_TYPES,
	IDENTIFIER_TYPES,
	ROLE_TYPES,
	_entity_snapshot,
	_related_records,
	_resolve_chain,
)
from nexora.directory.core import fingerprint, normalize_contact, normalize_identifier, normalize_name
from nexora.permissions import require_action


def get_entity(entity: str, include_sensitive: int = 0, resolve: int = 1) -> dict[str, Any]:
	require_action("read_entities")
	sensitive = bool(int(include_sensitive or 0))
	if sensitive:
		require_action("read_sensitive_entity")
	requested = entity
	canonical, chain = _resolve_chain(entity) if bool(int(resolve or 0)) else (entity, [entity])
	doc = frappe.get_doc("NXR Entity", canonical)
	result = _entity_snapshot(doc, include_sensitive=sensitive)
	result.update(_related_records(doc.name))
	result["requested_entity"] = requested
	result["canonical_entity"] = canonical
	result["redirect_chain"] = chain
	result["redirected"] = int(requested != canonical)
	return result


def search_entities(
	query: str | None = None, status: str | None = None, role_type: str | None = None, limit: int = 50
) -> list[dict[str, Any]]:
	require_action("read_entities")
	maximum = min(max(int(limit or 50), 1), 200)
	candidate_ids: set[str] = set()
	text = str(query or "").strip()
	if not text:
		filters = {"status": status} if status else None
		candidate_ids.update(
			row.name
			for row in frappe.get_all(
				"NXR Entity",
				filters=filters,
				fields=["name"],
				order_by="display_name asc",
				limit_page_length=maximum,
			)
		)
	else:
		like = f"%{text}%"
		candidate_ids.update(
			row.name
			for row in frappe.get_all(
				"NXR Entity",
				or_filters={
					"document_number": ["like", like],
					"display_name": ["like", like],
					"normalized_name": ["like", f"%{normalize_name(text)}%"],
				},
				fields=["name"],
				limit_page_length=maximum,
			)
		)
		identifier_hashes: set[str] = set()
		for kind in IDENTIFIER_TYPES:
			try:
				identifier_hashes.add(fingerprint("identifier", kind, normalize_identifier(kind, text)))
			except ValueError:
				continue
		if identifier_hashes:
			candidate_ids.update(
				row.parent
				for row in frappe.get_all(
					"NXR Entity Identifier",
					filters={"normalized_hash": ["in", sorted(identifier_hashes)]},
					fields=["parent"],
				)
			)
		contact_hashes: set[str] = set()
		for kind in CONTACT_TYPES:
			try:
				contact_hashes.add(fingerprint("contact", kind, normalize_contact(kind, text)))
			except ValueError:
				continue
		if contact_hashes:
			candidate_ids.update(
				row.parent
				for row in frappe.get_all(
					"NXR Entity Contact",
					filters={"normalized_hash": ["in", sorted(contact_hashes)]},
					fields=["parent"],
				)
			)
	resolved_role = str(role_type or "").strip().title()
	if resolved_role:
		if resolved_role not in ROLE_TYPES:
			frappe.throw(_("Tipo de rol no permitido para la búsqueda."))
		role_entities = {
			row.entity
			for row in frappe.get_all(
				"NXR Entity Role",
				filters={"role_type": resolved_role, "status": ["in", ["Proposed", "Active", "Suspended"]]},
				fields=["entity"],
			)
		}
		candidate_ids = candidate_ids.intersection(role_entities) if candidate_ids else role_entities
	rows: list[dict[str, Any]] = []
	for entity_name in candidate_ids:
		row = frappe.db.get_value(
			"NXR Entity",
			entity_name,
			["name", "document_number", "status", "entity_type", "display_name", "country", "merged_into"],
			as_dict=True,
		)
		if not row or (status and row.status != status):
			continue
		canonical, chain = _resolve_chain(row.name)
		rows.append(
			{
				"name": row.name,
				"document_number": row.document_number,
				"status": row.status,
				"entity_type": row.entity_type,
				"display_name": row.display_name,
				"country": row.country,
				"canonical_entity": canonical,
				"redirected": int(canonical != row.name),
				"redirect_chain": chain,
			}
		)
	return sorted(rows, key=lambda row: (row["display_name"], row["document_number"]))[:maximum]


def list_entities(
	query: str | None = None, status: str | None = None, limit: int = 50
) -> list[dict[str, Any]]:
	return search_entities(query=query, status=status, limit=limit)
