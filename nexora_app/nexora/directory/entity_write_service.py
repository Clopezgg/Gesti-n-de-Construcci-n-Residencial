from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.directory.common import (
	ENTITY_TYPES,
	_assert_identifier_availability,
	_assert_linked_user_availability,
	_contact_rows,
	_entity_snapshot,
	_identifier_rows,
	_lock,
	_lock_identifier_hashes,
	_lock_user,
	_required,
)
from nexora.directory.core import ENTITY_TRANSITIONS, assert_transition
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


def create_entity(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("create_entity")
	data = parse_payload(payload)
	entity_type = _required(data, "entity_type", "La entidad requiere tipo.").title()
	if entity_type not in ENTITY_TYPES:
		frappe.throw(_("Tipo de entidad no permitido."))
	display_name = _required(data, "display_name", "La entidad requiere nombre visible.")
	idempotency_key = _required(data, "idempotency_key", "La entidad requiere clave de idempotencia.")
	identifiers = _identifier_rows(data.get("identifiers"))
	contacts = _contact_rows(data.get("contacts"))
	linked_user = str(data.get("linked_user") or "").strip() or None
	fingerprint_data = {
		"entity_type": entity_type,
		"display_name": display_name,
		"legal_name": data.get("legal_name"),
		"linked_user": linked_user,
		"country": data.get("country"),
		"date_of_birth": data.get("date_of_birth"),
		"identifier_hashes": [row["normalized_hash"] for row in identifiers],
		"contact_hashes": [row["normalized_hash"] for row in contacts],
		"notes": data.get("notes"),
	}
	payload_hash = canonical_payload_hash(fingerprint_data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(idempotency_key, payload_hash, correlation_id)
		if cached is not None:
			return cached
		_lock_user(linked_user)
		_lock_identifier_hashes([row["normalized_hash"] for row in identifiers])
		_assert_identifier_availability(identifiers)
		_assert_linked_user_availability(linked_user)
		number, sequence = issue_document_number("NXR Entity", idempotency_key)
		with service_write():
			doc = frappe.get_doc(
				{
					"doctype": "NXR Entity",
					"document_number": number,
					"status": "Draft",
					"entity_type": entity_type,
					"display_name": display_name,
					"legal_name": data.get("legal_name"),
					"linked_user": linked_user,
					"country": data.get("country"),
					"date_of_birth": data.get("date_of_birth"),
					"identifiers": identifiers,
					"contacts": contacts,
					"notes": data.get("notes"),
					"idempotency_key": idempotency_key,
					"payload_hash": payload_hash,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
		link_sequence(sequence, doc.name)
		result = _entity_snapshot(doc)
		audit("entity_created", "NXR Entity", doc.name, payload_hash, correlation_id, result)
		complete_idempotency(idem, "NXR Entity", doc.name, result)
		return result
	except frappe.DuplicateEntryError:
		rollback(point)
		frappe.throw(_("La entidad contiene un identificador, usuario o clave ya registrados."))
	except Exception:
		rollback(point)
		raise


def update_entity(entity: str, payload: str | Mapping[str, Any], idempotency_key: str) -> dict[str, Any]:
	require_action("update_entity")
	data = parse_payload(payload)
	payload_hash = canonical_payload_hash({"entity": entity, "changes": data})
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(idempotency_key, payload_hash, correlation_id)
		if cached is not None:
			return cached
		doc = _lock("NXR Entity", entity)
		if doc.status in {"Inactive", "Consolidated"}:
			frappe.throw(_("Una entidad terminal no puede modificarse."))
		identifiers = _identifier_rows(data.get("identifiers")) if "identifiers" in data else None
		contacts = _contact_rows(data.get("contacts")) if "contacts" in data else None
		new_linked_user = (
			(str(data.get("linked_user") or "").strip() or None) if "linked_user" in data else doc.linked_user
		)
		_lock_user(new_linked_user)
		if identifiers is not None:
			_lock_identifier_hashes([row["normalized_hash"] for row in identifiers])
			_assert_identifier_availability(identifiers, doc.name)
		_assert_linked_user_availability(new_linked_user, doc.name)
		with service_write():
			for fieldname in (
				"display_name",
				"legal_name",
				"linked_user",
				"country",
				"date_of_birth",
				"notes",
			):
				if fieldname in data:
					doc.set(fieldname, data.get(fieldname) or None)
			if identifiers is not None:
				doc.set("identifiers", identifiers)
			if contacts is not None:
				doc.set("contacts", contacts)
			doc.save(ignore_permissions=True)
		result = _entity_snapshot(doc)
		audit("entity_updated", "NXR Entity", doc.name, payload_hash, correlation_id, result)
		complete_idempotency(idem, "NXR Entity", doc.name, result)
		return result
	except frappe.DuplicateEntryError:
		rollback(point)
		frappe.throw(_("La actualización contiene un identificador o usuario ya registrado."))
	except Exception:
		rollback(point)
		raise


def transition_entity(
	entity: str, status: str, idempotency_key: str, notes: str | None = None
) -> dict[str, Any]:
	require_action("manage_entity")
	target = str(status or "").strip().title()
	if target == "Consolidated":
		frappe.throw(_("Use el servicio de consolidación para ese estado."))
	payload = {"entity": entity, "status": target, "notes": notes or ""}
	payload_hash = canonical_payload_hash(payload)
	correlation_id = correlation(payload)
	point = savepoint()
	try:
		idem, cached = start_idempotency(idempotency_key, payload_hash, correlation_id)
		if cached is not None:
			return cached
		doc = _lock("NXR Entity", entity)
		try:
			assert_transition(str(doc.status), target, ENTITY_TRANSITIONS)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		with service_write():
			doc.status = target
			if notes:
				doc.notes = notes
			doc.save(ignore_permissions=True)
		result = _entity_snapshot(doc)
		audit("entity_transitioned", "NXR Entity", doc.name, payload_hash, correlation_id, result)
		complete_idempotency(idem, "NXR Entity", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise
