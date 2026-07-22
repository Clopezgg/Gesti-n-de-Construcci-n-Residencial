from __future__ import annotations

import json
import secrets
import unicodedata
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from erpnext.construcontrol.admin_corrections import (
	_correction_context,
	_evidence,
	_fingerprint,
	_reason,
	_require_token,
)
from erpnext.construcontrol.audit import record_manual_event

_MAX_DUPLICATES = 20
_SUPPORTED_LINKS: dict[tuple[str, str], tuple[str, ...]] = {
	("CC Expense Control", "supplier"): ("provider_name",),
	("CC Payable Control", "supplier"): ("provider_name", "supplier_name"),
	("CC Labor Contract", "supplier"): ("contractor_name",),
}


def _normalize_name(value: Any) -> str:
	text = unicodedata.normalize("NFKD", str(value or ""))
	plain = "".join(char for char in text if not unicodedata.combining(char))
	return " ".join("".join(char if char.isalnum() else " " for char in plain.casefold()).split())


def _parse_names(value: Any) -> list[str]:
	if isinstance(value, str):
		try:
			value = frappe.parse_json(value)
		except Exception:
			value = [part.strip() for part in value.split(",") if part.strip()]
	if not isinstance(value, list | tuple):
		frappe.throw(_("Seleccione uno o más proveedores duplicados."))
	result: list[str] = []
	for item in value:
		name = str(item or "").strip()
		if name and name not in result:
			result.append(name)
	if not result or len(result) > _MAX_DUPLICATES:
		frappe.throw(_("Seleccione entre 1 y {0} proveedores duplicados.").format(_MAX_DUPLICATES))
	return result


def _supplier_snapshot(name: str) -> dict[str, Any]:
	if not frappe.db.exists("Supplier", name):
		frappe.throw(_("El proveedor {0} no existe.").format(frappe.bold(name)))
	meta = frappe.get_meta("Supplier")
	fields = [
		field
		for field in (
			"name",
			"supplier_name",
			"tax_id",
			"disabled",
			"supplier_type",
			"supplier_group",
			"cc_normalized_name",
			"cc_merged_into",
			"cc_archived_duplicate",
			"cc_aliases_json",
		)
		if field == "name" or meta.has_field(field)
	]
	row = frappe.db.get_value("Supplier", name, fields, as_dict=True)
	return dict(row or {})


def _supplier_links() -> list[tuple[str, str]]:
	rows: set[tuple[str, str]] = set()
	for row in frappe.get_all(
		"DocField",
		filters={"fieldtype": "Link", "options": "Supplier"},
		fields=["parent", "fieldname"],
	):
		doctype = str(row.get("parent") or "")
		fieldname = str(row.get("fieldname") or "")
		if doctype and fieldname and doctype != "Supplier":
			rows.add((doctype, fieldname))
	for row in frappe.get_all(
		"Custom Field",
		filters={"fieldtype": "Link", "options": "Supplier"},
		fields=["dt", "fieldname"],
	):
		doctype = str(row.get("dt") or "")
		fieldname = str(row.get("fieldname") or "")
		if doctype and fieldname and doctype != "Supplier":
			rows.add((doctype, fieldname))
	return sorted(rows)


def _reference_report(supplier: str) -> dict[str, Any]:
	supported: list[dict[str, Any]] = []
	unsupported: list[dict[str, Any]] = []
	for doctype, fieldname in _supplier_links():
		if not frappe.db.exists("DocType", doctype):
			continue
		try:
			count = cint(frappe.db.count(doctype, {fieldname: supplier}))
		except Exception:
			count = 0
		if not count:
			continue
		row = {"doctype": doctype, "fieldname": fieldname, "count": count}
		(supported if (doctype, fieldname) in _SUPPORTED_LINKS else unsupported).append(row)

	if frappe.db.exists("DocType", "Contract"):
		contract_count = cint(frappe.db.count("Contract", {"party_type": "Supplier", "party_name": supplier}))
		if contract_count:
			supported.append({"doctype": "Contract", "fieldname": "party_name", "count": contract_count})

	if frappe.db.exists("DocType", "Dynamic Link"):
		dynamic_count = cint(
			frappe.db.count("Dynamic Link", {"link_doctype": "Supplier", "link_name": supplier})
		)
		if dynamic_count:
			supported.append({"doctype": "Dynamic Link", "fieldname": "link_name", "count": dynamic_count})
	return {
		"supplier": supplier,
		"supported": supported,
		"unsupported": unsupported,
		"supported_count": sum(row["count"] for row in supported),
		"unsupported_count": sum(row["count"] for row in unsupported),
	}


def _prepare(
	canonical_supplier: str,
	duplicate_suppliers: Any,
	reason: str,
	evidence: str,
) -> dict[str, Any]:
	canonical_supplier = str(canonical_supplier or "").strip()
	duplicates = _parse_names(duplicate_suppliers)
	if canonical_supplier in duplicates:
		frappe.throw(_("El proveedor oficial no puede aparecer entre los duplicados."))
	canonical = _supplier_snapshot(canonical_supplier)
	if cint(canonical.get("disabled")):
		frappe.throw(_("El proveedor oficial debe estar activo."))
	if cint(canonical.get("cc_archived_duplicate")) or canonical.get("cc_merged_into"):
		frappe.throw(_("El proveedor oficial ya está archivado como duplicado."))

	duplicate_rows = [_supplier_snapshot(name) for name in duplicates]
	for row in duplicate_rows:
		if row.get("cc_merged_into") and row.get("cc_merged_into") != canonical_supplier:
			frappe.throw(
				_("El proveedor {0} ya fue consolidado en otro registro.").format(
					frappe.bold(row.get("name"))
				)
			)
	reports = [_reference_report(name) for name in duplicates]
	unsupported = [row for report in reports for row in report["unsupported"]]
	reason = _reason(reason)
	evidence = _evidence(evidence, True)
	payload = {
		"canonical": canonical,
		"duplicates": duplicate_rows,
		"references": reports,
		"unsupported": unsupported,
		"blocked": bool(unsupported),
		"reason": reason,
		"evidence": evidence,
		"total_documents": sum(report["supported_count"] for report in reports),
	}
	payload["preview_hash"] = _fingerprint(payload)
	return payload


def _set_supported_reference(
	doctype: str,
	name: str,
	fieldname: str,
	canonical: str,
	canonical_label: str,
) -> None:
	meta = frappe.get_meta(doctype)
	updates: dict[str, Any] = {fieldname: canonical}
	for label_field in _SUPPORTED_LINKS.get((doctype, fieldname), ()):
		if meta.has_field(label_field):
			updates[label_field] = canonical_label
	frappe.db.set_value(doctype, name, updates, update_modified=True)


def _move_dynamic_links(duplicate: str, canonical: str) -> int:
	if not frappe.db.exists("DocType", "Dynamic Link"):
		return 0
	rows = frappe.get_all(
		"Dynamic Link",
		filters={"link_doctype": "Supplier", "link_name": duplicate},
		fields=["name", "parent", "parenttype", "parentfield"],
	)
	moved = 0
	for row in rows:
		existing = frappe.db.exists(
			"Dynamic Link",
			{
				"parent": row.parent,
				"parenttype": row.parenttype,
				"parentfield": row.parentfield,
				"link_doctype": "Supplier",
				"link_name": canonical,
			},
		)
		if existing:
			frappe.delete_doc("Dynamic Link", row.name, ignore_permissions=True, force=True)
		else:
			frappe.db.set_value("Dynamic Link", row.name, "link_name", canonical, update_modified=False)
		moved += 1
	return moved


def _merge_aliases(canonical: dict[str, Any], duplicates: list[dict[str, Any]]) -> str:
	aliases: set[str] = set()
	try:
		stored = frappe.parse_json(canonical.get("cc_aliases_json") or "[]") or []
		if isinstance(stored, list):
			aliases.update(str(item) for item in stored if item)
	except Exception:
		pass
	for row in duplicates:
		for value in (row.get("name"), row.get("supplier_name"), row.get("tax_id")):
			if value:
				aliases.add(str(value))
	return json.dumps(sorted(aliases), ensure_ascii=False)


def _recalculate_affected(funds: set[str], contracts: set[str], projects: set[str]) -> None:
	from erpnext.construcontrol.construction import recalculate_contract, recalculate_project_control
	from erpnext.construcontrol.finance import recalculate_funding_source

	for name in sorted(funds):
		recalculate_funding_source(name)
	for name in sorted(contracts):
		recalculate_contract(name)
	for project in sorted(projects):
		recalculate_project_control(project)


@frappe.whitelist(methods=["POST"])
def preview_supplier_consolidation(
	canonical_supplier: str,
	duplicate_suppliers: Any,
	reason: str,
	evidence: str,
	authorization_token: str,
) -> dict[str, Any]:
	_require_token(authorization_token)
	return _prepare(canonical_supplier, duplicate_suppliers, reason, evidence)


@frappe.whitelist(methods=["POST"])
def execute_supplier_consolidation(
	canonical_supplier: str,
	duplicate_suppliers: Any,
	reason: str,
	evidence: str,
	preview_hash: str,
	authorization_token: str,
) -> dict[str, Any]:
	authorization = _require_token(authorization_token)
	payload = _prepare(canonical_supplier, duplicate_suppliers, reason, evidence)
	if payload["blocked"]:
		labels = ", ".join(
			f"{row['doctype']}.{row['fieldname']} ({row['count']})" for row in payload["unsupported"]
		)
		frappe.throw(_("La consolidación está bloqueada por referencias no compatibles: {0}").format(labels))
	if not secrets.compare_digest(str(preview_hash or ""), payload["preview_hash"]):
		frappe.throw(_("La vista previa de proveedores cambió. Genérela nuevamente."))

	canonical = str(payload["canonical"]["name"])
	canonical_label = str(payload["canonical"].get("supplier_name") or canonical)
	duplicates = [str(row["name"]) for row in payload["duplicates"]]
	lock_key = "construcontrol:supplier-consolidation:" + _fingerprint([canonical, *duplicates])
	lock = frappe.cache.lock(lock_key, timeout=180, blocking_timeout=5)
	if not lock.acquire(blocking=True):
		frappe.throw(_("Existe otra consolidación sobre estos proveedores."))

	savepoint = f"cc_supplier_{frappe.generate_hash(length=12)}"
	frappe.db.savepoint(savepoint)
	moved: dict[str, int] = {}
	funds: set[str] = set()
	contracts: set[str] = set()
	projects: set[str] = set()
	try:
		with _correction_context():
			for duplicate in duplicates:
				for doctype, fieldname in _SUPPORTED_LINKS:
					if not frappe.db.exists("DocType", doctype):
						continue
					fields = ["name"]
					for extra in ("funding_source", "labor_contract", "project"):
						if frappe.get_meta(doctype).has_field(extra):
							fields.append(extra)
					rows = frappe.get_all(doctype, filters={fieldname: duplicate}, fields=fields)
					for row in rows:
						if row.get("funding_source"):
							funds.add(str(row.get("funding_source")))
						if row.get("labor_contract"):
							contracts.add(str(row.get("labor_contract")))
						if row.get("project"):
							projects.add(str(row.get("project")))
						_set_supported_reference(doctype, row.name, fieldname, canonical, canonical_label)
					moved[f"{doctype}.{fieldname}"] = moved.get(f"{doctype}.{fieldname}", 0) + len(rows)

				if frappe.db.exists("DocType", "Contract"):
					contract_names = frappe.get_all(
						"Contract",
						filters={"party_type": "Supplier", "party_name": duplicate},
						pluck="name",
					)
					for name in contract_names:
						frappe.db.set_value("Contract", name, "party_name", canonical, update_modified=True)
					moved["Contract.party_name"] = moved.get("Contract.party_name", 0) + len(contract_names)

				dynamic = _move_dynamic_links(duplicate, canonical)
				moved["Dynamic Link.link_name"] = moved.get("Dynamic Link.link_name", 0) + dynamic
				updates = {
					"disabled": 1,
					"cc_normalized_name": _normalize_name(payload["canonical"].get("supplier_name")),
					"cc_merged_into": canonical,
					"cc_archived_duplicate": 1,
				}
				frappe.db.set_value("Supplier", duplicate, updates, update_modified=True)

			canonical_updates = {
				"disabled": 0,
				"cc_normalized_name": _normalize_name(canonical_label),
				"cc_aliases_json": _merge_aliases(payload["canonical"], payload["duplicates"]),
			}
			frappe.db.set_value("Supplier", canonical, canonical_updates, update_modified=True)
			_recalculate_affected(funds, contracts, projects)
			record_manual_event(
				module="FI02",
				action="ADMIN_CONSOLIDATE_SUPPLIERS",
				record_type="Supplier",
				record_id=canonical,
				reason=payload["reason"],
				previous_state={
					"canonical": payload["canonical"],
					"duplicates": payload["duplicates"],
					"references": payload["references"],
				},
				next_state={
					"canonical": _supplier_snapshot(canonical),
					"duplicates": [_supplier_snapshot(name) for name in duplicates],
					"moved": moved,
					"evidence": payload["evidence"],
					"authorization_id": authorization["authorization_id"],
				},
				origin="ADMIN_CORRECTION",
				correlation_id=authorization["authorization_id"],
			)
		frappe.db.release_savepoint(savepoint)
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise
	finally:
		try:
			lock.release()
		except Exception:
			pass
	return {
		"canonical_supplier": canonical,
		"archived_duplicates": duplicates,
		"moved": moved,
		"authorization_id": authorization["authorization_id"],
	}


__all__ = ["execute_supplier_consolidation", "preview_supplier_consolidation"]
