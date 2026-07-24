from __future__ import annotations

from typing import Any

import frappe
from frappe import _


def _password(row: Any, fieldname: str) -> str | None:
	try:
		return row.get_password(fieldname, raise_exception=False)
	except Exception:
		return None


def _entity_snapshot(doc: Any, *, include_sensitive: bool = False) -> dict[str, Any]:
	identifiers: list[dict[str, Any]] = []
	for row in doc.identifiers:
		item = {
			"name": row.name,
			"identifier_type": row.identifier_type,
			"masked_value": row.masked_value,
			"is_primary": int(row.is_primary or 0),
			"valid_from": row.valid_from,
			"valid_until": row.valid_until,
		}
		if include_sensitive:
			item["identifier_value"] = _password(row, "identifier_value")
			item["normalized_hash"] = row.normalized_hash
		identifiers.append(item)
	contacts: list[dict[str, Any]] = []
	for row in doc.contacts:
		item = {
			"name": row.name,
			"contact_type": row.contact_type,
			"masked_value": row.masked_value,
			"is_primary": int(row.is_primary or 0),
			"is_verified": int(row.is_verified or 0),
			"valid_from": row.valid_from,
			"valid_until": row.valid_until,
		}
		if include_sensitive:
			item["contact_value"] = _password(row, "contact_value")
			item["normalized_hash"] = row.normalized_hash
		contacts.append(item)
	result = {
		"name": doc.name,
		"document_number": doc.document_number,
		"status": doc.status,
		"entity_type": doc.entity_type,
		"display_name": doc.display_name,
		"normalized_name": doc.normalized_name,
		"country": doc.country,
		"merged_into": doc.merged_into,
		"consolidation_record": doc.consolidation_record,
		"notes": doc.notes,
		"identifiers": identifiers,
		"contacts": contacts,
	}
	if include_sensitive:
		result.update(
			{"legal_name": doc.legal_name, "linked_user": doc.linked_user, "date_of_birth": doc.date_of_birth}
		)
	return result


def _related_records(entity: str) -> dict[str, list[dict[str, Any]]]:
	return {
		"roles": frappe.get_all(
			"NXR Entity Role",
			filters={"entity": entity},
			fields=["name", "document_number", "status", "role_type", "project", "valid_from", "valid_until"],
			order_by="valid_from desc, creation desc",
		),
		"compliance": frappe.get_all(
			"NXR Entity Compliance",
			filters={"entity": entity},
			fields=[
				"name",
				"document_number",
				"status",
				"compliance_type",
				"valid_from",
				"valid_until",
				"evidence",
			],
			order_by="creation desc",
		),
	}


def _resolve_chain(entity: str) -> tuple[str, list[str]]:
	chain: list[str] = []
	current = entity
	for _depth in range(100):
		if current in chain:
			frappe.throw(_("Se detectó un ciclo de consolidación."))
		chain.append(current)
		row = frappe.db.get_value("NXR Entity", current, ["status", "merged_into"], as_dict=True)
		if not row:
			frappe.throw(_("La entidad indicada no existe."))
		if row.status != "Consolidated" or not row.merged_into:
			return current, chain
		current = str(row.merged_into)
	frappe.throw(_("La cadena de consolidación excede el límite seguro."))


def _reference_counts(entity: str) -> dict[str, int]:
	return {
		"identifiers": frappe.db.count("NXR Entity Identifier", {"parent": entity}),
		"contacts": frappe.db.count("NXR Entity Contact", {"parent": entity}),
		"roles": frappe.db.count("NXR Entity Role", {"entity": entity}),
		"compliance": frappe.db.count("NXR Entity Compliance", {"entity": entity}),
	}
