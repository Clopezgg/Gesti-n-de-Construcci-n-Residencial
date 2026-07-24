from __future__ import annotations

from typing import Any, Sequence

import frappe
from frappe import _


def _lock(doctype: str, name: str) -> Any:
	table = frappe.qb.DocType(doctype)
	rows = frappe.qb.from_(table).select(table.name).where(table.name == name).for_update().run()
	if not rows:
		frappe.throw(_("El documento {0} no existe.").format(name))
	return frappe.get_doc(doctype, name)


def _lock_user(linked_user: str | None) -> None:
	if not linked_user:
		return
	if linked_user == "Guest":
		frappe.throw(_("Guest no puede vincularse como entidad."))
	rows = frappe.db.sql("SELECT name FROM `tabUser` WHERE name=%s FOR UPDATE", linked_user)
	if not rows:
		frappe.throw(_("El usuario vinculado no existe."))


def _lock_identifier_hashes(hashes: Sequence[str]) -> None:
	ordered = sorted(set(hashes))
	if not ordered:
		return
	identifier = frappe.qb.DocType("NXR Entity Identifier")
	frappe.qb.from_(identifier).select(identifier.name).where(
		identifier.normalized_hash.isin(ordered)
	).orderby(identifier.normalized_hash).for_update().run()


def _assert_identifier_availability(rows: list[dict[str, Any]], exclude_entity: str | None = None) -> None:
	hashes = [row["normalized_hash"] for row in rows]
	if not hashes:
		return
	matches = frappe.db.get_all(
		"NXR Entity Identifier",
		filters={"normalized_hash": ["in", hashes]},
		fields=["parent", "masked_value"],
	)
	conflicts = [row for row in matches if row.parent != exclude_entity]
	if conflicts:
		frappe.throw(_("El identificador {0} ya pertenece a otra entidad.").format(conflicts[0].masked_value))


def _assert_linked_user_availability(linked_user: str | None, exclude_entity: str | None = None) -> None:
	if not linked_user:
		return
	match = frappe.db.get_value(
		"NXR Entity", {"linked_user": linked_user, "status": ["!=", "Consolidated"]}, "name"
	)
	if match and match != exclude_entity:
		frappe.throw(_("El usuario ya está vinculado a otra entidad no consolidada."))
