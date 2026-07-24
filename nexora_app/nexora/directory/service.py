from __future__ import annotations

from typing import Any, Mapping

import frappe

from nexora.directory.compliance_service import (
	create_entity_compliance as _create_entity_compliance,
	transition_entity_compliance as _transition_entity_compliance,
)
from nexora.directory.consolidation_service import (
	consolidate_entities as _consolidate_entities,
	resolve_canonical_entity as _resolve_canonical_entity,
)
from nexora.directory.duplicate_service import detect_entity_duplicates as _detect_entity_duplicates
from nexora.directory.entity_read_service import (
	get_entity as _get_entity,
	list_entities as _list_entities,
	search_entities as _search_entities,
)
from nexora.directory.entity_write_service import (
	create_entity as _create_entity,
	transition_entity as _transition_entity,
	update_entity as _update_entity,
)
from nexora.directory.role_service import (
	assign_entity_role as _assign_entity_role,
	transition_entity_role as _transition_entity_role,
)


@frappe.whitelist(methods=["POST"])
def create_entity(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	return _create_entity(payload)


@frappe.whitelist(methods=["POST"])
def update_entity(entity: str, payload: str | Mapping[str, Any], idempotency_key: str) -> dict[str, Any]:
	return _update_entity(entity, payload, idempotency_key)


@frappe.whitelist(methods=["POST"])
def transition_entity(
	entity: str, status: str, idempotency_key: str, notes: str | None = None
) -> dict[str, Any]:
	return _transition_entity(entity, status, idempotency_key, notes)


@frappe.whitelist(methods=["POST"])
def get_entity(entity: str, include_sensitive: int = 0, resolve: int = 1) -> dict[str, Any]:
	return _get_entity(entity, include_sensitive, resolve)


@frappe.whitelist(methods=["POST"])
def search_entities(
	query: str | None = None, status: str | None = None, role_type: str | None = None, limit: int = 50
) -> list[dict[str, Any]]:
	return _search_entities(query, status, role_type, limit)


@frappe.whitelist(methods=["POST"])
def list_entities(
	query: str | None = None, status: str | None = None, limit: int = 50
) -> list[dict[str, Any]]:
	return _list_entities(query, status, limit)


@frappe.whitelist(methods=["POST"])
def detect_entity_duplicates(payload: str | Mapping[str, Any]) -> list[dict[str, Any]]:
	return _detect_entity_duplicates(payload)


@frappe.whitelist(methods=["POST"])
def assign_entity_role(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	return _assign_entity_role(payload)


@frappe.whitelist(methods=["POST"])
def transition_entity_role(
	role: str, status: str, idempotency_key: str, notes: str | None = None
) -> dict[str, Any]:
	return _transition_entity_role(role, status, idempotency_key, notes)


@frappe.whitelist(methods=["POST"])
def create_entity_compliance(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	return _create_entity_compliance(payload)


@frappe.whitelist(methods=["POST"])
def transition_entity_compliance(
	compliance: str,
	status: str,
	idempotency_key: str,
	notes: str | None = None,
	evidence: str | None = None,
) -> dict[str, Any]:
	return _transition_entity_compliance(compliance, status, idempotency_key, notes, evidence)


@frappe.whitelist(methods=["POST"])
def consolidate_entities(source: str, target: str, reason: str, idempotency_key: str) -> dict[str, Any]:
	return _consolidate_entities(source, target, reason, idempotency_key)


@frappe.whitelist(methods=["POST"])
def resolve_canonical_entity(entity: str) -> dict[str, Any]:
	return _resolve_canonical_entity(entity)
