from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import frappe
from frappe import _
from frappe.utils.pdf import get_pdf
from frappe.utils.xlsxutils import make_xlsx

from nexora.dashboard.executive import get_contract_page, get_source_statement_page
from nexora.dashboard.expense_query import get_expense_page
from nexora.dashboard.snapshot_query import get_executive_snapshot
from nexora.financial.core import canonical_payload_hash
from nexora.financial.db import audit, correlation
from nexora.permissions import require_action
from nexora.reports.service import EXPORT_ROW_LIMIT, _data, _html_report, _project, _report_code

PAGINATED_REPORT_LOADERS: dict[str, Callable[[dict[str, Any]], Mapping[str, Any]]] = {
	"FI01": get_source_statement_page,
	"FI02": get_expense_page,
	"CO01": get_contract_page,
}


def _assert_export_size(data: Mapping[str, Any], report_code: str) -> None:
	loader = PAGINATED_REPORT_LOADERS.get(report_code)
	if not loader:
		return
	page = loader({**data, "page": 1, "page_size": 1})
	total = int(page.get("pagination", {}).get("total") or 0)
	if total > EXPORT_ROW_LIMIT:
		frappe.throw(
			_("El reporte contiene {0} filas y supera el límite autorizado de {1}.").format(
				total,
				EXPORT_ROW_LIMIT,
			)
		)


def _collect_pages(
	loader: Callable[[dict[str, Any]], Mapping[str, Any]],
	data: Mapping[str, Any],
) -> list[dict[str, Any]]:
	rows: list[dict[str, Any]] = []
	page_number = 1
	while True:
		response = loader({**data, "page": page_number, "page_size": 100})
		batch = [dict(row) for row in response.get("rows", [])]
		total = int(response.get("pagination", {}).get("total") or len(rows) + len(batch))
		if total > EXPORT_ROW_LIMIT:
			frappe.throw(
				_("El reporte contiene {0} filas y supera el límite autorizado de {1}.").format(
					total,
					EXPORT_ROW_LIMIT,
				)
			)
		rows.extend(batch)
		if not batch or len(rows) >= total:
			return rows
		page_number += 1


def _paginated_rows(data: Mapping[str, Any], code: str) -> tuple[list[str], list[list[Any]]] | None:
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
	return None


def _snapshot_rows(data: Mapping[str, Any], code: str) -> tuple[list[str], list[list[Any]]]:
	paginated = _paginated_rows(data, code)
	if paginated is not None:
		return paginated
	snapshot = get_executive_snapshot(data)
	analytics = snapshot.get("analytics", {})
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


@frappe.whitelist(methods=["POST"])
def export_report(payload: str | Mapping[str, Any]) -> None:
	"""Export canonical filtered rows and reject oversized reports without truncation."""
	data = _data(payload)
	require_action("export_reports")
	_project(data, "export_reports")
	code = _report_code(data)
	file_format = str(data.get("format") or "xlsx").strip().lower()
	if file_format not in {"xlsx", "pdf"}:
		frappe.throw(_("El formato de exportación debe ser Excel o PDF."))
	_assert_export_size(data, code)
	headers, rows = _snapshot_rows(data, code)
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
			"filters": {
				key: data.get(key)
				for key in (
					"from_date",
					"to_date",
					"source",
					"economic_category",
					"cost_center",
					"entity",
					"payment_method",
					"contractor",
					"contract_status",
				)
				if data.get(key)
			},
		},
	)
	frappe.local.response.filename = filename
	frappe.local.response.filecontent = content
	frappe.local.response.type = "download"
	frappe.local.response.display_content_as = "attachment"
