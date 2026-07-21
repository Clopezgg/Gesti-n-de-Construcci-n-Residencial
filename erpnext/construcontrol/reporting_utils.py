from __future__ import annotations

import hashlib
import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

from erpnext.construcontrol.access import (
	assert_project_access,
)

_READER_ROLES = {
	"System Manager",
	"ConstruControl Manager",
	"ConstruControl Operator",
	"ConstruControl Auditor",
	"ConstruControl Viewer",
}
_WRITER_ROLES = {"System Manager", "ConstruControl Manager", "ConstruControl Operator"}
_EXPORT_ROLES = {"System Manager", "ConstruControl Manager", "ConstruControl Auditor"}
_ROLE_LABELS = (
	("System Manager", "ADMIN"),
	("ConstruControl Manager", "MANAGER"),
	("ConstruControl Operator", "OPERATOR"),
	("ConstruControl Auditor", "AUDITOR"),
	("ConstruControl Viewer", "VIEWER"),
)


def _require(roles: set[str], message: str) -> None:
	if not (roles & set(frappe.get_roles())):
		frappe.throw(_(message), frappe.PermissionError)


def _role_label() -> str:
	roles = set(frappe.get_roles())
	for role, label in _ROLE_LABELS:
		if role in roles:
			return label
	return "USER"


def _full_name(user: str) -> str:
	return str(frappe.db.get_value("User", user, "full_name") or user)


def _period(date_from: str | None, date_to: str | None) -> tuple[Any, Any]:
	start = getdate(date_from) if date_from else getdate(today()).replace(day=1)
	end = getdate(date_to) if date_to else getdate(today())
	if start > end:
		frappe.throw(_("La fecha inicial no puede ser posterior a la fecha final."))
	return start, end


def _fields(doctype: str, requested: list[str]) -> list[str]:
	meta = frappe.get_meta(doctype)
	return [field for field in requested if field == "name" or meta.has_field(field)]


def _between(start: Any, end: Any) -> list[Any]:
	return ["between", [start, end]]


def _active_contract(row: Any) -> bool:
	return str(row.get("status") or "").strip().casefold() not in {
		"cancelled",
		"canceled",
		"rejected",
		"reimbursed",
	}


def _weighted_progress(phases: list[Any]) -> float:
	weighted = 0.0
	weight_total = 0.0
	for row in phases:
		weight = flt(row.get("budget_hnl")) or 1.0
		weighted += max(0.0, min(flt(row.get("progress_percent")), 100.0)) * weight
		weight_total += weight
	return round(weighted / weight_total, 2) if weight_total else 0.0


def sanitize_csv_cell(value: Any) -> str:
	"""Prevent spreadsheet formula execution while preserving the visible value."""
	text = "" if value is None else str(value)
	trimmed = text.lstrip()
	if trimmed.startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
		return "'" + text
	return text


def deterministic_report_key(
	report_type: str,
	project: str,
	date_from: str,
	date_to: str,
	payload: dict[str, Any],
) -> str:
	canonical = json.dumps(
		{
			"report_type": str(report_type).strip().casefold(),
			"project": str(project).strip(),
			"date_from": str(date_from),
			"date_to": str(date_to),
			"payload": payload,
		},
		ensure_ascii=False,
		sort_keys=True,
		default=str,
		separators=(",", ":"),
	)
	return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _require_exact_project(project: str | None, *, write: bool = False) -> str:
	if not str(project or "").strip():
		frappe.throw(_("Seleccione un proyecto antes de generar o exportar el reporte."))
	return assert_project_access(str(project), write=write)


__all__ = [
	"_EXPORT_ROLES",
	"_READER_ROLES",
	"_WRITER_ROLES",
	"_active_contract",
	"_between",
	"_fields",
	"_full_name",
	"_period",
	"_require",
	"_require_exact_project",
	"_role_label",
	"_weighted_progress",
	"deterministic_report_key",
	"sanitize_csv_cell",
]
