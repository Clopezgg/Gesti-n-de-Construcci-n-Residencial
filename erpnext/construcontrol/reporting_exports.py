from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from typing import Any

import frappe
from frappe import _
from frappe.utils import now_datetime, today

from erpnext.construcontrol.access import require_construcontrol_access
from erpnext.construcontrol.reporting_summary import get_reporting_summary
from erpnext.construcontrol.reporting_utils import (
	_EXPORT_ROLES,
	_WRITER_ROLES,
	_full_name,
	_require,
	_require_exact_project,
	_role_label,
	deterministic_report_key,
	sanitize_csv_cell,
)


@frappe.whitelist(methods=["POST"])
def generate_report_record(
	report_type: str,
	date_from: str | None = None,
	date_to: str | None = None,
	project: str | None = None,
) -> dict[str, Any]:
	_require(_WRITER_ROLES, "No tiene permiso para generar registros de reporte.")
	require_construcontrol_access(write=True)
	project = _require_exact_project(project, write=True)
	allowed = {
		"financial",
		"expenses",
		"contracts",
		"phases",
		"inventory",
		"quality",
		"weekly",
	}
	normalized_type = str(report_type or "financial").strip().casefold()
	if normalized_type not in allowed:
		frappe.throw(_("Tipo de reporte no permitido."))

	summary = get_reporting_summary(date_from=date_from, date_to=date_to, project=project)
	key_payload = {"totals": summary["totals"], "counts": summary["counts"]}
	full_hash = deterministic_report_key(
		normalized_type,
		project,
		summary["period"]["date_from"],
		summary["period"]["date_to"],
		key_payload,
	)
	source_key = full_hash[:40]
	existing = frappe.db.get_value(
		"CC Generated Report",
		{"source_key": source_key, "is_logically_deleted": 0},
		"name",
	)
	if existing:
		return {"name": existing, "reused": True, "summary": summary}

	user = frappe.session.user
	title = (
		f"BI01 · {normalized_type.upper()} · "
		f"{summary['period']['date_from']} a {summary['period']['date_to']}"
	)
	values = {
		"doctype": "CC Generated Report",
		"source_key": source_key,
		"source_id": source_key,
		"project": project,
		"code": f"BI01-{source_key[:10].upper()}",
		"title": title,
		"status": "generated",
		"posting_date": today(),
		"amount_hnl": summary["totals"]["spent_hnl"],
		"description": "Reporte generado desde servicios canónicos y registros vivos de ConstruControl.",
		"report_type": normalized_type,
		"date_from": summary["period"]["date_from"],
		"date_to": summary["period"]["date_to"],
		"generated_at": now_datetime(),
		"generated_by_email": user,
		"generated_by_name": _full_name(user),
		"generated_by_role": _role_label(),
		"filters_json": json.dumps({"project": project}, ensure_ascii=False, sort_keys=True),
		"totals_json": json.dumps(summary["totals"], ensure_ascii=False, sort_keys=True),
		"export_sha256": full_hash,
		"payload_json": json.dumps(summary, ensure_ascii=False, sort_keys=True, default=str),
		"is_logically_deleted": 0,
	}
	allowed_fields = {field.fieldname for field in frappe.get_meta("CC Generated Report").fields}
	document = frappe.get_doc(
		{key: value for key, value in values.items() if key == "doctype" or key in allowed_fields}
	)
	document.insert()
	return {"name": document.name, "reused": False, "summary": summary}


def _csv_content(summary: dict[str, Any]) -> str:
	buffer = io.StringIO(newline="")
	writer = csv.writer(buffer)
	writer.writerow(["ConstruControl BI01", "Valor"])
	writer.writerow(["Proyecto", sanitize_csv_cell(summary.get("project"))])
	writer.writerow(["Desde", sanitize_csv_cell(summary["period"]["date_from"])])
	writer.writerow(["Hasta", sanitize_csv_cell(summary["period"]["date_to"])])
	writer.writerow([])
	writer.writerow(["Indicador", "Monto/valor"])
	for key, value in summary["totals"].items():
		writer.writerow([sanitize_csv_cell(key), sanitize_csv_cell(value)])
	writer.writerow([])
	writer.writerow(["Conteo", "Cantidad"])
	for key, value in summary["counts"].items():
		writer.writerow([sanitize_csv_cell(key), sanitize_csv_cell(value)])
	writer.writerow([])
	writer.writerow(["Categoría de gasto", "Monto HNL"])
	for row in summary.get("expense_categories") or []:
		writer.writerow(
			[
				sanitize_csv_cell(row.get("label")),
				sanitize_csv_cell(row.get("amount_hnl")),
			]
		)
	writer.writerow([])
	writer.writerow(["Proveedor", "Monto HNL"])
	for row in summary.get("providers") or []:
		writer.writerow(
			[
				sanitize_csv_cell(row.get("label")),
				sanitize_csv_cell(row.get("amount_hnl")),
			]
		)
	return "\ufeff" + buffer.getvalue()


@frappe.whitelist(methods=["POST"])
def export_report_csv(
	report_type: str = "financial",
	date_from: str | None = None,
	date_to: str | None = None,
	project: str | None = None,
) -> dict[str, Any]:
	_require(_EXPORT_ROLES, "No tiene permiso para exportar reportes de ConstruControl.")
	require_construcontrol_access()
	project = _require_exact_project(project)
	summary = get_reporting_summary(date_from=date_from, date_to=date_to, project=project)
	content = _csv_content(summary)
	content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
	profile = frappe.db.get_value(
		"CC Project Profile",
		{"project": project, "is_logically_deleted": 0},
		"name",
	)
	if not profile:
		frappe.throw(_("El proyecto no tiene un perfil ConstruControl para proteger la exportación."))
	file_name = (
		f"construcontrol-{re.sub(r'[^a-zA-Z0-9_-]+', '-', project).strip('-').lower()}-"
		f"{summary['period']['date_from']}-{summary['period']['date_to']}-{content_hash[:12]}.csv"
	)
	existing = frappe.db.get_value(
		"File",
		{
			"file_name": file_name,
			"is_private": 1,
			"attached_to_doctype": "CC Project Profile",
			"attached_to_name": profile,
		},
		["name", "file_url"],
		as_dict=True,
	)
	if existing:
		return {
			"file": existing.name,
			"file_url": existing.file_url,
			"sha256": content_hash,
			"reused": True,
		}
	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": file_name,
			"is_private": 1,
			"content": content,
			"attached_to_doctype": "CC Project Profile",
			"attached_to_name": profile,
			"attached_to_field": "",
		}
	).insert(ignore_permissions=True)
	from erpnext.construcontrol.audit import record_manual_event

	record_manual_event(
		module="BI01",
		action="EXPORT",
		record_type="CC Project Profile",
		record_id=profile,
		project=project,
		reason=f"Exportación privada CSV {report_type}",
		next_state={"file_name": file_name, "sha256": content_hash},
		origin="API",
	)
	return {
		"file": file_doc.name,
		"file_url": file_doc.file_url,
		"sha256": content_hash,
		"reused": False,
	}


__all__ = ["export_report_csv", "generate_report_record"]
