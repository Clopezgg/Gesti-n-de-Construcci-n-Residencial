from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

import frappe
from frappe import _
from frappe.utils.pdf import get_pdf
from frappe.utils.xlsxutils import make_xlsx
from markupsafe import escape

from nexora.dashboard.executive import (
	get_contract_page,
	get_executive_snapshot,
	get_expense_page,
	get_source_movement_page,
	get_source_statement_page,
)
from nexora.financial.context import service_write
from nexora.financial.core import canonical_payload_hash, money
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
from nexora.permissions import require_action, require_project_access
from nexora.reports.core import format_statement_rows, reconcile_amounts

REPORT_CODES = {"BI01", "FI01", "FI02", "FI03", "CO01", "PR02", "PR03", "MM03"}
EXPORT_ROW_LIMIT = 5000


def _data(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	return parse_payload(payload)


def _project(data: Mapping[str, Any], action: str = "view_reports") -> str | None:
	project = str(data.get("project") or "").strip() or None
	require_project_access(project, action=action)
	return project


def _report_code(data: Mapping[str, Any]) -> str:
	code = str(data.get("report_code") or "BI01").strip().upper()
	if code not in REPORT_CODES:
		frappe.throw(_("El tipo de reporte solicitado no está habilitado."))
	return code


def _operation_statement(filters: dict[str, Any]) -> dict[str, Any]:
	try:
		operations = frappe.get_all(
			"NXR Operation",
			fields=[
				"name",
				"document_number",
				"operation_type",
				"amount_hnl",
				"status",
				"operation_date",
				"creation",
				"description",
			],
			filters=filters,
			order_by="operation_date asc, creation asc",
			limit_page_length=1000,
		)
	except (frappe.DoesNotExistError, frappe.ValidationError):
		operations = []
	return {
		"totals": reconcile_amounts(operations),
		"rows": format_statement_rows(operations),
		"row_count": len(operations),
	}


def _collect_pages(
	loader: Callable[[dict[str, Any]], Mapping[str, Any]],
	data: Mapping[str, Any],
) -> list[dict[str, Any]]:
	rows: list[dict[str, Any]] = []
	page = 1
	while len(rows) < EXPORT_ROW_LIMIT:
		response = loader({**data, "page": page, "page_size": 100})
		batch = [dict(row) for row in response.get("rows", [])]
		rows.extend(batch)
		total = int(response.get("pagination", {}).get("total") or len(rows))
		if not batch or len(rows) >= total:
			break
		page += 1
	return rows[:EXPORT_ROW_LIMIT]


@frappe.whitelist(methods=["POST"])
def get_source_statement(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = _data(payload)
	require_action("view_financial_details")
	_project(data, "view_financial_details")
	source = str(data.get("source") or "").strip()
	if not source:
		frappe.throw(_("Seleccione una fuente de fondos."))
	summary_page = get_source_statement_page({**data, "source": source, "page": 1, "page_size": 1})
	return {
		"source": source,
		"summary": summary_page.get("rows", [{}])[0] if summary_page.get("rows") else {},
		"movements": get_source_movement_page(data),
	}


@frappe.whitelist(methods=["POST"])
def get_entity_statement(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = _data(payload)
	require_action("view_financial_details")
	project = _project(data, "view_financial_details")
	entity = str(data.get("entity") or "").strip()
	if not entity:
		frappe.throw(_("Seleccione una entidad."))
	filters: dict[str, Any] = {"beneficiary": entity}
	if project:
		filters["project"] = project
	return {"entity": entity, **_operation_statement(filters)}


@frappe.whitelist(methods=["POST"])
def get_contract_statement(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = _data(payload)
	contract = str(data.get("contract") or "").strip()
	if not contract:
		frappe.throw(_("Seleccione un contrato."))
	# NXR-SEC-0001 (Bloque 19): el permiso se comprobaba contra `data["project"]`
	# (declarado por el cliente), no contra el proyecto real del `contract`
	# consultado. Un "NEXORA Project Viewer" restringido al Proyecto A podía enviar
	# `project=A` (pasaba el chequeo) y `contract=<de otro proyecto>`: el resumen
	# salía vacío pero `transactions` (montos, fechas, descripciones) del contrato
	# ajeno se devolvía completa. Corregido resolviendo el proyecto desde el propio
	# documento antes de comprobar acceso — mismo patrón que
	# `financial/service.py::reconcile_fund_source`.
	contract_project = frappe.db.get_value("NXR Contract", contract, "project")
	require_project_access(contract_project, action="view_reports")
	summary_page = get_contract_page({**data, "contract": contract, "page": 1, "page_size": 1})
	summary = summary_page.get("rows", [{}])[0] if summary_page.get("rows") else {}
	transactions = frappe.get_all(
		"NXR Contract Transaction",
		filters={"contract": contract, "status": ["!=", "Reversed"]},
		fields=[
			"name",
			"document_number",
			"transaction_type",
			"effective_date",
			"amount",
			"linked_operation",
			"status",
			"description",
			"reversal_of",
		],
		order_by="effective_date asc, creation asc",
		limit_page_length=1000,
	)
	exchange_rate = money(summary.get("exchange_rate") or 1)
	rows = [
		{
			**dict(row),
			"amount_hnl": money(row.get("amount")) * exchange_rate,
		}
		for row in transactions
	]
	return {
		"contract": contract,
		"summary": summary,
		"totals": {
			"contract_value_hnl": summary.get("contract_value_hnl", 0),
			"executed_hnl": summary.get("executed_hnl", 0),
			"paid_hnl": summary.get("paid_hnl", 0),
			"balance_hnl": summary.get("balance_hnl", 0),
			"retention_balance_hnl": summary.get("retention_balance_hnl", 0),
		},
		"rows": rows,
		"row_count": len(rows),
	}


@frappe.whitelist(methods=["POST"])
def get_financial_report(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = _data(payload)
	require_action("view_reports")
	_project(data)
	return get_executive_snapshot(data)


@frappe.whitelist(methods=["POST"])
def get_cost_report(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = _data(payload)
	require_action("view_financial_details")
	_project(data, "view_financial_details")
	snapshot = get_executive_snapshot(data)
	categories = snapshot.get("analytics", {}).get("expenses_by_category", [])
	return {
		"categories": {str(row.get("label")): row.get("amount_hnl", 0) for row in categories},
		"total": snapshot.get("executive", {}).get("spent_hnl", 0),
	}


@frappe.whitelist(methods=["POST"])
def reconcile_totals(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = _data(payload)
	require_action("view_financial_details")
	project = _project(data, "view_financial_details")
	snapshot = get_executive_snapshot(data)
	totals = snapshot.get("analytics", {}).get("source_totals", {})
	operation_filters = {"project": project} if project else {}
	return {
		"inflows": totals.get("received_hnl", 0),
		"outflows": totals.get("spent_hnl", 0),
		"net": totals.get("closing_available_hnl", 0),
		"operation_count": frappe.db.count("NXR Operation", filters=operation_filters),
	}


def _snapshot_rows(data: Mapping[str, Any], code: str) -> tuple[list[str], list[list[Any]]]:
	snapshot = get_executive_snapshot(data)
	analytics = snapshot.get("analytics", {})
	if code == "FI01":
		rows = _collect_pages(get_source_statement_page, data)
		return (
			[
				"Fuente",
				"Fecha",
				"Remitente",
				"Canal",
				"Moneda",
				"Importe original",
				"Tasa",
				"Recibido HNL",
				"Gastado HNL",
				"Transferencia entrada HNL",
				"Transferencia salida HNL",
				"Reservado HNL",
				"Liberado HNL",
				"Saldo inicial HNL",
				"Saldo cierre HNL",
				"Disponible cierre HNL",
				"Saldo actual HNL",
				"Conciliación",
				"Proyecto",
			],
			[
				[
					row.get("source_code") or row.get("name"),
					row.get("source_date"),
					row.get("origin_or_sender"),
					row.get("channel"),
					row.get("currency"),
					row.get("original_amount"),
					row.get("exchange_rate"),
					row.get("received_hnl"),
					row.get("spent_hnl"),
					row.get("transfer_in_hnl"),
					row.get("transfer_out_hnl"),
					row.get("reserved_hnl"),
					row.get("released_hnl"),
					row.get("opening_funds_hnl"),
					row.get("closing_funds_hnl"),
					row.get("closing_available_hnl"),
					row.get("current_funds_hnl"),
					row.get("reconciliation_status"),
					row.get("project"),
				]
				for row in rows
			],
		)
	if code == "FI02":
		rows = _collect_pages(get_expense_page, data)
		return (
			[
				"Documento",
				"Fecha",
				"Proveedor",
				"Categoría",
				"Centro de costo",
				"Fuentes",
				"Medio de pago",
				"Referencia",
				"Importe HNL",
				"Estado",
				"Proyecto",
			],
			[
				[
					row.get("document_number") or row.get("name"),
					row.get("operation_date"),
					row.get("beneficiary_label"),
					row.get("economic_category"),
					row.get("cost_center"),
					row.get("sources"),
					row.get("payment_method"),
					row.get("external_reference"),
					row.get("amount_hnl"),
					row.get("status"),
					row.get("project"),
				]
				for row in rows
			],
		)
	if code == "CO01":
		rows = _collect_pages(get_contract_page, data)
		return (
			[
				"Contrato",
				"Contratista",
				"Estado",
				"Inicio",
				"Fin vigente",
				"Valor HNL",
				"Ejecutado HNL",
				"Pagado HNL",
				"Saldo HNL",
				"Anticipo HNL",
				"Amortizado HNL",
				"Retención HNL",
				"Multas",
				"Deducciones",
				"Versión",
				"Proyecto",
			],
			[
				[
					row.get("document_number") or row.get("name"),
					row.get("contractor_label"),
					row.get("status"),
					row.get("start_date"),
					row.get("current_end_date"),
					row.get("contract_value_hnl"),
					row.get("executed_hnl"),
					row.get("paid_hnl"),
					row.get("balance_hnl"),
					row.get("advance_disbursed"),
					row.get("advance_amortized"),
					row.get("retention_balance"),
					row.get("fine_amount"),
					row.get("deduction_amount"),
					row.get("version"),
					row.get("project"),
				]
				for row in rows
			],
		)
	if code == "FI03":
		return (
			["Documento", "Beneficiario", "Vencimiento", "Importe HNL", "Situación"],
			[
				[
					row.get("document_number"),
					row.get("beneficiary") or row.get("title"),
					row.get("due_date"),
					row.get("amount_hnl"),
					row.get("due_state"),
				]
				for row in snapshot.get("pending_accounts", {}).get("items", [])
			],
		)
	if code == "PR02":
		return (
			["Categoría", "Aprobado HNL", "Comprometido HNL", "Ejecutado HNL", "Disponible HNL"],
			[
				[
					row.get("label"),
					row.get("approved_hnl"),
					row.get("committed_hnl"),
					row.get("executed_hnl"),
					row.get("available_hnl"),
				]
				for row in snapshot.get("budgets", {}).get("lines", [])
			],
		)
	if code == "PR03":
		progress = snapshot.get("progress", {})
		operational = progress.get("operational", {})
		return ["Métrica", "Valor"], [
			["Avance físico (%)", progress.get("physical_percent", 0)],
			["Avance financiero (%)", snapshot.get("executive", {}).get("financial_percent", 0)],
			["Contratos activos", operational.get("active_contracts", 0)],
			["Solicitudes pendientes", operational.get("pending_requests", 0)],
			["Órdenes abiertas", operational.get("open_orders", 0)],
			["Calidad pendiente", operational.get("open_quality_issues", 0)],
		]
	if code == "MM03":
		return ["Artículo", "Bodega", "Saldo"], [
			[row.get("item"), row.get("warehouse"), row.get("balance_qty")]
			for row in analytics.get("critical_inventory", [])
		]
	executive = snapshot.get("executive", {})
	return ["Indicador", "Valor"], [
		["Recibido HNL", executive.get("received_hnl", 0)],
		["Gastado HNL", executive.get("spent_hnl", 0)],
		["Pagado HNL", executive.get("paid_hnl", 0)],
		["Caja disponible HNL", executive.get("cash_available_hnl", 0)],
		["Comprometido HNL", executive.get("committed_hnl", 0)],
		["Presupuesto disponible HNL", executive.get("budget_available_hnl", 0)],
		["Disponible proyectado HNL", executive.get("projected_available_hnl", 0)],
	]


def _html_report(code: str, headers: list[str], rows: list[list[Any]], data: Mapping[str, Any]) -> str:
	def escaped(value: object) -> str:
		return str(escape(str(value if value is not None else "")))

	period = f"{escaped(data.get('from_date') or 'inicio')} — {escaped(data.get('to_date') or 'actual')}"
	project = escaped(data.get("project") or "Todos los proyectos")
	head = "".join(f"<th>{escaped(header)}</th>" for header in headers)
	body = "".join("<tr>" + "".join(f"<td>{escaped(value)}</td>" for value in row) + "</tr>" for row in rows)
	return f"""
	<html><head><meta charset="utf-8"><style>
	body{{font-family:Arial,sans-serif;color:#172033;font-size:9px}}
	h1{{font-size:19px;margin:0}} .meta{{margin:6px 0 14px;color:#526078}}
	table{{border-collapse:collapse;width:100%}} th,td{{border:1px solid #d8dee9;padding:5px;text-align:left}}
	th{{background:#eef3f8;font-weight:700}} tr:nth-child(even){{background:#fafbfd}}
	</style></head><body><h1>NEXORA · {escaped(code)}</h1>
	<div class="meta">Gestión Integral de Fondos, Proyectos y Operaciones · {project} · {period}</div>
	<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></body></html>
	"""


@frappe.whitelist(methods=["POST"])
def export_report(payload: str | Mapping[str, Any]) -> None:
	data = _data(payload)
	require_action("export_reports")
	_project(data, "export_reports")
	code = _report_code(data)
	file_format = str(data.get("format") or "xlsx").strip().lower()
	if file_format not in {"xlsx", "pdf"}:
		frappe.throw(_("El formato de exportación debe ser Excel o PDF."))
	headers, rows = _snapshot_rows(data, code)
	if len(rows) > EXPORT_ROW_LIMIT:
		frappe.throw(_("El reporte supera el límite de exportación autorizado."))
	if file_format == "xlsx":
		content = make_xlsx([headers, *rows], code).getvalue()
		filename = f"NEXORA-{code}-{frappe.utils.today()}.xlsx"
	else:
		content = get_pdf(_html_report(code, headers, rows, data), {"orientation": "Landscape"})
		filename = f"NEXORA-{code}-{frappe.utils.today()}.pdf"
	fingerprint = canonical_payload_hash({**data, "row_count": len(rows)})
	correlation_id = correlation(data)
	audit(
		"report_exported",
		"Project" if data.get("project") else "User",
		str(data.get("project") or frappe.session.user),
		fingerprint,
		correlation_id,
		{
			"report_code": code,
			"format": file_format,
			"row_count": len(rows),
			"project": data.get("project"),
		},
	)
	frappe.local.response.filename = filename
	frappe.local.response.filecontent = content
	frappe.local.response.type = "download"
	frappe.local.response.display_content_as = "attachment"


@frappe.whitelist(methods=["POST"])
def save_report_definition(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = _data(payload)
	require_action("view_reports")
	project = _project(data)
	code = _report_code(data)
	title = str(data.get("title") or f"{code} · Reporte guardado").strip()[:140]
	key = str(data.get("idempotency_key") or "").strip()
	filters = dict(data.get("filters") or {})
	normalized = {"title": title, "report_code": code, "project": project, "filters": filters}
	fingerprint = canonical_payload_hash(normalized)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		number, sequence = issue_document_number("NXR Saved Report", key)
		with service_write():
			doc = frappe.get_doc(
				{
					"doctype": "NXR Saved Report",
					"document_number": number,
					"status": "Active",
					"title": title,
					"report_code": code,
					"project": project,
					"filters_json": json.dumps(filters, ensure_ascii=False, sort_keys=True, default=str),
					"owner_user": frappe.session.user,
					"idempotency_key": key,
					"payload_hash": fingerprint,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
		link_sequence(sequence, doc.name)
		result = {
			"saved_report": doc.name,
			"document_number": number,
			"title": title,
			"report_code": code,
			"project": project,
			"filters": filters,
		}
		audit("saved_report_created", "NXR Saved Report", doc.name, fingerprint, correlation_id, result)
		complete_idempotency(idem, "NXR Saved Report", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def list_saved_reports(payload: str | Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
	data = _data(payload or {})
	require_action("view_reports")
	project = _project(data)
	filters: dict[str, Any] = {"owner_user": frappe.session.user, "status": "Active"}
	if project:
		filters["project"] = project
	rows = frappe.get_all(
		"NXR Saved Report",
		filters=filters,
		fields=[
			"name",
			"document_number",
			"title",
			"report_code",
			"project",
			"filters_json",
			"modified",
		],
		order_by="modified desc",
		limit_page_length=50,
	)
	for row in rows:
		try:
			row["filters"] = json.loads(row.get("filters_json") or "{}")
		except (TypeError, ValueError):
			row["filters"] = {}
		row.pop("filters_json", None)
	return rows


@frappe.whitelist(methods=["POST"])
def reconcile_fund_source(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = _data(payload)
	require_action("reconcile_source")
	source_name = str(data.get("source") or "").strip()
	if not source_name:
		frappe.throw(_("Seleccione el registro de fondos que desea conciliar."))
	status = str(data.get("status") or "Reconciled").strip().title()
	if status not in {"Pending", "Reconciled", "Disputed"}:
		frappe.throw(_("El estado de conciliación no es válido."))
	method = str(data.get("method") or "").strip()
	note = str(data.get("note") or "").strip()
	evidence = str(data.get("evidence") or "").strip() or None
	difference = money(data.get("difference_hnl"))
	if status != "Pending" and not method:
		frappe.throw(_("Indique el método utilizado para conciliar."))
	if (status == "Disputed" or difference != 0) and not note:
		frappe.throw(_("Explique la diferencia detectada durante la conciliación."))
	if (status == "Disputed" or difference != 0) and not evidence:
		frappe.throw(_("Adjunte evidencia para una conciliación con diferencia."))
	key = str(data.get("idempotency_key") or "").strip()
	normalized = {
		"source": source_name,
		"status": status,
		"method": method,
		"difference_hnl": str(difference),
		"note": note,
		"evidence": evidence,
	}
	fingerprint = canonical_payload_hash(normalized)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		locked = frappe.db.sql("SELECT name FROM `tabNXR Fund Source` WHERE name=%s FOR UPDATE", source_name)
		if not locked:
			frappe.throw(_("El registro de fondos indicado no existe."))
		doc = frappe.get_doc("NXR Fund Source", source_name)
		require_project_access(doc.project, action="reconcile_source")
		with service_write():
			doc.reconciliation_status = status
			doc.reconciliation_method = method or None
			doc.reconciliation_difference_hnl = difference
			doc.reconciliation_note = note or None
			doc.reconciliation_evidence = evidence
			doc.reconciled_by = frappe.session.user if status != "Pending" else None
			doc.reconciled_at = frappe.utils.now_datetime() if status != "Pending" else None
			doc.save(ignore_permissions=True)
		result = {
			"fund_source": doc.name,
			"reconciliation_status": status,
			"reconciliation_method": method,
			"reconciliation_difference_hnl": f"{difference:.2f}",
			"reconciled_by": doc.reconciled_by,
			"reconciled_at": doc.reconciled_at,
		}
		audit("fund_source_reconciled", "NXR Fund Source", doc.name, fingerprint, correlation_id, result)
		complete_idempotency(idem, "NXR Fund Source", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise
