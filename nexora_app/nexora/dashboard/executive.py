from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

import frappe
from frappe import _

from nexora.dashboard.analytics_core import normalize_period, number
from nexora.dashboard.service import get_dashboard_summary
from nexora.permissions import require_action, require_project_access

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100
DASHBOARD_PAGE_SIZE = 8


def _payload(value: str | Mapping[str, Any]) -> dict[str, Any]:
	data = dict(value) if isinstance(value, Mapping) else frappe.parse_json(value)
	if not isinstance(data, dict):
		frappe.throw(_("El payload analítico debe ser un objeto JSON."))
	return data


def _text(data: Mapping[str, Any], fieldname: str) -> str | None:
	value = str(data.get(fieldname) or "").strip()
	return value or None


def _period(data: Mapping[str, Any]) -> tuple[str, str]:
	try:
		return normalize_period(data.get("from_date"), data.get("to_date"))
	except (TypeError, ValueError) as exc:
		frappe.throw(_(str(exc)))
		raise AssertionError from exc


def _pagination(data: Mapping[str, Any], default_size: int = DEFAULT_PAGE_SIZE) -> tuple[int, int, int]:
	page = max(int(data.get("page") or 1), 1)
	page_size = min(max(int(data.get("page_size") or default_size), 1), MAX_PAGE_SIZE)
	return page, page_size, (page - 1) * page_size


def _project(data: Mapping[str, Any]) -> str | None:
	project = _text(data, "project")
	require_project_access(project, action="view_reports")
	return project


def _source_effect_aggregates(source_names: list[str], start: str, end: str) -> dict[str, dict[str, Any]]:
	if not source_names:
		return {}
	rows = frappe.db.sql(
		"""
		SELECT e.fund_source,
			COALESCE(SUM(CASE WHEN e.dimension='Funds' AND o.operation_date < %(start)s THEN e.amount_hnl ELSE 0 END),0) opening_funds_hnl,
			COALESCE(SUM(CASE WHEN e.dimension='Reserved' AND o.operation_date < %(start)s THEN e.amount_hnl ELSE 0 END),0) opening_reserved_hnl,
			COALESCE(SUM(CASE WHEN e.dimension='Funds' AND o.operation_date <= %(end)s THEN e.amount_hnl ELSE 0 END),0) closing_funds_hnl,
			COALESCE(SUM(CASE WHEN e.dimension='Reserved' AND o.operation_date <= %(end)s THEN e.amount_hnl ELSE 0 END),0) closing_reserved_hnl,
			COALESCE(SUM(CASE WHEN e.dimension='Funds' THEN e.amount_hnl ELSE 0 END),0) current_funds_hnl,
			COALESCE(SUM(CASE WHEN e.dimension='Reserved' THEN e.amount_hnl ELSE 0 END),0) current_reserved_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND e.dimension='Funds' AND o.operation_type='Inflow' AND e.amount_hnl>0 THEN e.amount_hnl ELSE 0 END),0) received_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND e.dimension='Funds' AND o.operation_type IN ('Outflow','Commitment Execution') AND e.amount_hnl<0 THEN -e.amount_hnl ELSE 0 END),0) spent_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND e.dimension='Funds' AND o.operation_type='Internal Transfer' AND e.amount_hnl>0 THEN e.amount_hnl ELSE 0 END),0) transfer_in_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND e.dimension='Funds' AND o.operation_type='Internal Transfer' AND e.amount_hnl<0 THEN -e.amount_hnl ELSE 0 END),0) transfer_out_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND e.dimension='Funds' AND o.operation_type='Real Return' THEN ABS(e.amount_hnl) ELSE 0 END),0) returned_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND e.is_reversal=1 THEN ABS(e.amount_hnl) ELSE 0 END),0) reversed_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND e.dimension='Reserved' AND e.amount_hnl>0 THEN e.amount_hnl ELSE 0 END),0) reserved_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND e.dimension='Reserved' AND e.amount_hnl<0 THEN -e.amount_hnl ELSE 0 END),0) released_hnl
		FROM `tabNXR Operation Effect` e
		INNER JOIN `tabNXR Operation` o ON o.name=e.operation
		WHERE e.fund_source IN %(sources)s AND o.status NOT IN ('Draft','Cancelled')
		GROUP BY e.fund_source
		""",
		{"sources": tuple(source_names), "start": start, "end": end},
		as_dict=True,
	)
	return {str(row.fund_source): dict(row) for row in rows}


def _source_statement(data: Mapping[str, Any], *, default_page_size: int = DEFAULT_PAGE_SIZE) -> dict[str, Any]:
	project = _project(data)
	start, end = _period(data)
	page, page_size, offset = _pagination(data, default_page_size)
	filters: list[list[Any]] = [["status", "!=", "Draft"]]
	for fieldname, value in (
		("project", project),
		("name", _text(data, "source")),
		("status", _text(data, "source_status")),
	):
		if value:
			filters.append([fieldname, "=", value])
	fields = [
		"name",
		"source_code",
		"source_name",
		"source_date",
		"channel",
		"project",
		"currency",
		"original_amount",
		"exchange_rate",
		"amount_hnl",
		"origin_or_sender",
		"custodian",
		"institution",
		"account_reference",
		"external_reference",
		"evidence",
		"reconciliation_status",
		"reconciled_by",
		"reconciled_at",
		"reconciliation_method",
		"reconciliation_difference_hnl",
		"reconciliation_note",
		"reconciliation_evidence",
		"status",
	]
	rows = frappe.get_all(
		"NXR Fund Source",
		fields=fields,
		filters=filters,
		order_by="source_date desc, creation desc",
		limit_start=offset,
		limit_page_length=page_size,
	)
	aggregates = _source_effect_aggregates([str(row.name) for row in rows], start, end)
	statement = []
	for row in rows:
		values = aggregates.get(str(row.name), {})
		closing_funds = Decimal(str(values.get("closing_funds_hnl") or 0))
		closing_reserved = Decimal(str(values.get("closing_reserved_hnl") or 0))
		current_funds = Decimal(str(values.get("current_funds_hnl") or 0))
		current_reserved = Decimal(str(values.get("current_reserved_hnl") or 0))
		statement.append(
			{
				**dict(row),
				**{key: number(value) for key, value in values.items() if key != "fund_source"},
				"closing_available_hnl": number(closing_funds - closing_reserved),
				"current_available_hnl": number(current_funds - current_reserved),
				"projected_hnl": None,
				"projection_basis": "La proyección se calcula a nivel de proyecto con obligaciones pendientes.",
				"reconciliation_status": row.get("reconciliation_status") or "Pending",
			}
		)
	return {
		"rows": statement,
		"pagination": {
			"page": page,
			"page_size": page_size,
			"total": int(frappe.db.count("NXR Fund Source", filters=filters)),
		},
		"period": {"from_date": start, "to_date": end},
	}


def _source_movement_page(data: Mapping[str, Any]) -> dict[str, Any]:
	project = _project(data)
	start, end = _period(data)
	page, page_size, offset = _pagination(data)
	source = _text(data, "source")
	if not source:
		frappe.throw(_("Seleccione una fuente para consultar sus movimientos."))
	conditions = [
		"e.fund_source=%(source)s",
		"o.operation_date BETWEEN %(start)s AND %(end)s",
		"o.status NOT IN ('Draft','Cancelled')",
	]
	params: dict[str, Any] = {
		"source": source,
		"start": start,
		"end": end,
		"limit": page_size,
		"offset": offset,
	}
	if project:
		conditions.append("o.project=%(project)s")
		params["project"] = project
	where = " AND ".join(conditions)
	rows = frappe.db.sql(
		f"""
		SELECT e.name,e.operation,o.document_number,o.operation_date,o.operation_type,o.status,
			e.dimension,e.effect_type,e.amount_hnl,e.cost_center,e.economic_category,e.is_reversal,
			e.reverses_effect,e.correlation_id
		FROM `tabNXR Operation Effect` e
		INNER JOIN `tabNXR Operation` o ON o.name=e.operation
		WHERE {where}
		ORDER BY o.operation_date DESC,o.creation DESC,e.creation DESC
		LIMIT %(limit)s OFFSET %(offset)s
		""",
		params,
		as_dict=True,
	)
	count = frappe.db.sql(
		f"""SELECT COUNT(*) FROM `tabNXR Operation Effect` e
		INNER JOIN `tabNXR Operation` o ON o.name=e.operation WHERE {where}""",
		params,
	)[0][0]
	return {
		"source": source,
		"rows": [{**dict(row), "amount_hnl": number(row.amount_hnl)} for row in rows],
		"pagination": {"page": page, "page_size": page_size, "total": int(count)},
		"period": {"from_date": start, "to_date": end},
	}


def _source_totals(project: str | None, start: str, end: str) -> dict[str, float]:
	project_sql = "AND o.project=%(project)s" if project else ""
	row = frappe.db.sql(
		f"""
		SELECT
			COALESCE(SUM(CASE WHEN e.dimension='Funds' AND o.operation_date < %(start)s THEN e.amount_hnl ELSE 0 END),0) opening_funds_hnl,
			COALESCE(SUM(CASE WHEN e.dimension='Reserved' AND o.operation_date < %(start)s THEN e.amount_hnl ELSE 0 END),0) opening_reserved_hnl,
			COALESCE(SUM(CASE WHEN e.dimension='Funds' AND o.operation_date <= %(end)s THEN e.amount_hnl ELSE 0 END),0) closing_funds_hnl,
			COALESCE(SUM(CASE WHEN e.dimension='Reserved' AND o.operation_date <= %(end)s THEN e.amount_hnl ELSE 0 END),0) closing_reserved_hnl,
			COALESCE(SUM(CASE WHEN e.dimension='Funds' THEN e.amount_hnl ELSE 0 END),0) current_funds_hnl,
			COALESCE(SUM(CASE WHEN e.dimension='Reserved' THEN e.amount_hnl ELSE 0 END),0) current_reserved_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND e.dimension='Funds' AND o.operation_type='Inflow' AND e.amount_hnl>0 THEN e.amount_hnl ELSE 0 END),0) received_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND e.dimension='Funds' AND o.operation_type IN ('Outflow','Commitment Execution') AND e.amount_hnl<0 THEN -e.amount_hnl ELSE 0 END),0) spent_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND e.dimension='Funds' AND o.operation_type='Internal Transfer' AND e.amount_hnl>0 THEN e.amount_hnl ELSE 0 END),0) transfer_in_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND e.dimension='Funds' AND o.operation_type='Internal Transfer' AND e.amount_hnl<0 THEN -e.amount_hnl ELSE 0 END),0) transfer_out_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND e.dimension='Funds' AND o.operation_type='Real Return' THEN ABS(e.amount_hnl) ELSE 0 END),0) returned_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND e.is_reversal=1 THEN ABS(e.amount_hnl) ELSE 0 END),0) reversed_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND e.dimension='Reserved' AND e.amount_hnl>0 THEN e.amount_hnl ELSE 0 END),0) reserved_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND e.dimension='Reserved' AND e.amount_hnl<0 THEN -e.amount_hnl ELSE 0 END),0) released_hnl
		FROM `tabNXR Operation Effect` e
		INNER JOIN `tabNXR Operation` o ON o.name=e.operation
		WHERE o.status NOT IN ('Draft','Cancelled') {project_sql}
		""",
		{"project": project, "start": start, "end": end},
		as_dict=True,
	)[0]
	result = {key: number(value) for key, value in row.items()}
	for prefix in ("opening", "closing", "current"):
		result[f"{prefix}_available_hnl"] = number(
			Decimal(str(row.get(f"{prefix}_funds_hnl") or 0))
			- Decimal(str(row.get(f"{prefix}_reserved_hnl") or 0))
		)
	return result


def _income_by_channel(project: str | None, start: str, end: str) -> list[dict[str, Any]]:
	project_sql = "AND o.project=%(project)s" if project else ""
	rows = frappe.db.sql(
		f"""
		SELECT COALESCE(s.channel,'Other') label,COALESCE(SUM(e.amount_hnl),0) amount_hnl
		FROM `tabNXR Operation Effect` e
		INNER JOIN `tabNXR Operation` o ON o.name=e.operation
		INNER JOIN `tabNXR Fund Source` s ON s.name=e.fund_source
		WHERE o.status NOT IN ('Draft','Cancelled') AND o.operation_type='Inflow'
			AND e.dimension='Funds' AND e.amount_hnl>0
			AND o.operation_date BETWEEN %(start)s AND %(end)s {project_sql}
		GROUP BY s.channel ORDER BY amount_hnl DESC
		""",
		{"project": project, "start": start, "end": end},
		as_dict=True,
	)
	return [{"label": row.label, "amount_hnl": number(row.amount_hnl)} for row in rows]


def _expense_summary(project: str | None, start: str, end: str) -> dict[str, Any]:
	project_sql = "AND o.project=%(project)s" if project else ""
	params = {"project": project, "start": start, "end": end}
	categories = frappe.db.sql(
		f"""
		SELECT COALESCE(o.economic_category,'Sin clasificar') code,
			COALESCE(ec.category_name,o.economic_category,'Sin clasificar') label,
			COALESCE(SUM(ABS(o.amount_hnl)),0) amount_hnl,COUNT(*) operation_count
		FROM `tabNXR Operation` o
		LEFT JOIN `tabNXR Economic Category` ec ON ec.name=o.economic_category
		WHERE o.status='Executed' AND o.operation_type IN ('Outflow','Commitment Execution')
			AND o.operation_date BETWEEN %(start)s AND %(end)s {project_sql}
		GROUP BY o.economic_category,ec.category_name ORDER BY amount_hnl DESC LIMIT 20
		""",
		params,
		as_dict=True,
	)
	providers = frappe.db.sql(
		f"""
		SELECT COALESCE(e.display_name,o.beneficiary,'Sin beneficiario') label,
			COALESCE(SUM(ABS(o.amount_hnl)),0) amount_hnl,COUNT(*) operation_count
		FROM `tabNXR Operation` o
		LEFT JOIN `tabNXR Entity` e ON e.name=o.beneficiary AND o.beneficiary_doctype='NXR Entity'
		WHERE o.status='Executed' AND o.operation_type IN ('Outflow','Commitment Execution')
			AND o.operation_date BETWEEN %(start)s AND %(end)s {project_sql}
		GROUP BY o.beneficiary,e.display_name ORDER BY amount_hnl DESC LIMIT 10
		""",
		params,
		as_dict=True,
	)
	return {
		"expenses_by_category": [
			{
				"code": row.code,
				"label": row.label,
				"amount_hnl": number(row.amount_hnl),
				"operation_count": int(row.operation_count),
			}
			for row in categories
		],
		"providers": [
			{
				"label": row.label,
				"amount_hnl": number(row.amount_hnl),
				"operation_count": int(row.operation_count),
			}
			for row in providers
		],
	}


def _expense_page(data: Mapping[str, Any]) -> dict[str, Any]:
	project = _project(data)
	start, end = _period(data)
	page, page_size, offset = _pagination(data)
	conditions = [
		"o.status='Executed'",
		"o.operation_type IN ('Outflow','Commitment Execution')",
		"o.operation_date BETWEEN %(start)s AND %(end)s",
	]
	params: dict[str, Any] = {"start": start, "end": end, "limit": page_size, "offset": offset}
	for fieldname, column, value in (
		("project", "o.project", project),
		("economic_category", "o.economic_category", _text(data, "economic_category")),
		("entity", "o.beneficiary", _text(data, "entity")),
	):
		if value:
			conditions.append(f"{column}=%({fieldname})s")
			params[fieldname] = value
	source = _text(data, "source")
	if source:
		conditions.append(
			"EXISTS (SELECT 1 FROM `tabNXR Fund Allocation` x WHERE x.operation=o.name AND x.fund_source=%(source)s)"
		)
		params["source"] = source
	where = " AND ".join(conditions)
	rows = frappe.db.sql(
		f"""
		SELECT o.name,o.document_number,o.operation_date,o.operation_code,o.operation_type,o.project,
			o.cost_center,o.economic_category,o.beneficiary_doctype,o.beneficiary,
			COALESCE(e.display_name,o.beneficiary,'Sin beneficiario') beneficiary_label,
			o.payment_method,o.external_reference,ABS(o.amount_hnl) amount_hnl,o.status,
			GROUP_CONCAT(DISTINCT a.fund_source ORDER BY a.allocation_order SEPARATOR ', ') sources
		FROM `tabNXR Operation` o
		LEFT JOIN `tabNXR Entity` e ON e.name=o.beneficiary AND o.beneficiary_doctype='NXR Entity'
		LEFT JOIN `tabNXR Fund Allocation` a ON a.operation=o.name
		WHERE {where}
		GROUP BY o.name ORDER BY o.operation_date DESC,o.creation DESC
		LIMIT %(limit)s OFFSET %(offset)s
		""",
		params,
		as_dict=True,
	)
	count = frappe.db.sql(f"SELECT COUNT(*) FROM `tabNXR Operation` o WHERE {where}", params)[0][0]
	return {
		"rows": [{**dict(row), "amount_hnl": number(row.amount_hnl)} for row in rows],
		"pagination": {"page": page, "page_size": page_size, "total": int(count)},
		"period": {"from_date": start, "to_date": end},
	}


def _contract_page(data: Mapping[str, Any], *, default_size: int = DEFAULT_PAGE_SIZE) -> dict[str, Any]:
	project = _project(data)
	start, end = _period(data)
	page, page_size, offset = _pagination(data, default_size)
	conditions = [
		"c.status!='Cancelled Before Active'",
		"c.start_date<=%(end)s",
		"(c.current_end_date IS NULL OR c.current_end_date>=%(start)s)",
	]
	params: dict[str, Any] = {"start": start, "end": end, "limit": page_size, "offset": offset}
	for fieldname, column, value in (
		("project", "c.project", project),
		("contract", "c.name", _text(data, "contract")),
		("contractor", "c.contractor", _text(data, "contractor")),
		("contract_status", "c.status", _text(data, "contract_status")),
	):
		if value:
			conditions.append(f"{column}=%({fieldname})s")
			params[fieldname] = value
	where = " AND ".join(conditions)
	rows = frappe.db.sql(
		f"""
		SELECT c.name,c.document_number,c.contractor,COALESCE(e.display_name,c.contractor) contractor_label,
			c.project,c.status,c.start_date,c.current_end_date,c.currency,c.exchange_rate,c.current_amount,
			c.executed_amount,c.pending_amount,c.paid_amount,c.advance_disbursed,c.advance_amortized,
			c.advance_balance,c.retention_held,c.retention_returned,c.retention_balance,c.fine_amount,
			c.deduction_amount,c.version,
			(c.current_amount*COALESCE(c.exchange_rate,1)) contract_value_hnl,
			(c.executed_amount*COALESCE(c.exchange_rate,1)) executed_hnl,
			(c.paid_amount*COALESCE(c.exchange_rate,1)) paid_hnl,
			(c.pending_amount*COALESCE(c.exchange_rate,1)) balance_hnl
		FROM `tabNXR Contract` c LEFT JOIN `tabNXR Entity` e ON e.name=c.contractor
		WHERE {where} ORDER BY c.start_date DESC,c.modified DESC
		LIMIT %(limit)s OFFSET %(offset)s
		""",
		params,
		as_dict=True,
	)
	count = frappe.db.sql(f"SELECT COUNT(*) FROM `tabNXR Contract` c WHERE {where}", params)[0][0]
	money_fields = {
		"contract_value_hnl",
		"executed_hnl",
		"paid_hnl",
		"balance_hnl",
		"advance_disbursed",
		"advance_amortized",
		"advance_balance",
		"retention_held",
		"retention_returned",
		"retention_balance",
		"fine_amount",
		"deduction_amount",
	}
	prepared = []
	for row in rows:
		item = dict(row)
		for fieldname in money_fields:
			item[fieldname] = number(item.get(fieldname))
		prepared.append(item)
	return {
		"rows": prepared,
		"pagination": {"page": page, "page_size": page_size, "total": int(count)},
		"period": {"from_date": start, "to_date": end},
	}


def _contract_totals(project: str | None, start: str, end: str) -> dict[str, float | int]:
	project_sql = "AND c.project=%(project)s" if project else ""
	row = frappe.db.sql(
		f"""
		SELECT COUNT(*) contract_count,
			COALESCE(SUM(c.current_amount*COALESCE(c.exchange_rate,1)),0) contract_value_hnl,
			COALESCE(SUM(c.executed_amount*COALESCE(c.exchange_rate,1)),0) executed_hnl,
			COALESCE(SUM(c.paid_amount*COALESCE(c.exchange_rate,1)),0) paid_hnl,
			COALESCE(SUM(c.pending_amount*COALESCE(c.exchange_rate,1)),0) balance_hnl,
			COALESCE(SUM(c.retention_balance*COALESCE(c.exchange_rate,1)),0) retention_balance_hnl
		FROM `tabNXR Contract` c
		WHERE c.status!='Cancelled Before Active' AND c.start_date<=%(end)s
			AND (c.current_end_date IS NULL OR c.current_end_date>=%(start)s) {project_sql}
		""",
		{"project": project, "start": start, "end": end},
		as_dict=True,
	)[0]
	return {
		"contract_count": int(row.contract_count),
		"contract_value_hnl": number(row.contract_value_hnl),
		"executed_hnl": number(row.executed_hnl),
		"paid_hnl": number(row.paid_hnl),
		"balance_hnl": number(row.balance_hnl),
		"retention_balance_hnl": number(row.retention_balance_hnl),
	}


def _critical_inventory(project: str | None) -> list[dict[str, Any]]:
	project_sql = "AND t.project=%(project)s" if project else ""
	try:
		rows = frappe.db.sql(
			f"""
			SELECT l.item,l.warehouse,COALESCE(SUM(CASE
				WHEN t.transaction_type IN ('Receipt','Transfer In','Return') THEN l.quantity
				WHEN t.transaction_type IN ('Transfer Out','Issue to Contractor','Consumption','Damage','Loss') THEN -l.quantity
				ELSE 0 END),0) balance_qty
			FROM `tabNXR Stock Transaction Line` l
			INNER JOIN `tabNXR Stock Transaction` t ON t.name=l.parent
			WHERE t.status='Completed' {project_sql}
			GROUP BY l.item,l.warehouse HAVING balance_qty<=0
			ORDER BY balance_qty ASC,l.item ASC LIMIT 8
			""",
			{"project": project},
			as_dict=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "NEXORA critical inventory analytics")
		return []
	return [{"item": row.item, "warehouse": row.warehouse, "balance_qty": float(row.balance_qty)} for row in rows]


@frappe.whitelist(methods=["POST"])
def get_source_statement_page(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("view_financial_details")
	return _source_statement(_payload(payload))


@frappe.whitelist(methods=["POST"])
def get_source_movement_page(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("view_financial_details")
	return _source_movement_page(_payload(payload))


@frappe.whitelist(methods=["POST"])
def get_expense_page(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("view_financial_details")
	return _expense_page(_payload(payload))


@frappe.whitelist(methods=["POST"])
def get_contract_page(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("view_reports")
	return _contract_page(_payload(payload))


@frappe.whitelist(methods=["POST"])
def get_executive_snapshot(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("view_reports")
	data = _payload(payload)
	project = _project(data)
	start, end = _period(data)
	base = get_dashboard_summary({"project": project})
	source_page = _source_statement({**data, "page": 1, "page_size": DASHBOARD_PAGE_SIZE})
	expense_page = _expense_page({**data, "page": 1, "page_size": DASHBOARD_PAGE_SIZE})
	contract_page = _contract_page({**data, "page": 1, "page_size": DASHBOARD_PAGE_SIZE})
	source_totals = _source_totals(project, start, end)
	contract_totals = _contract_totals(project, start, end)
	expense_summary = _expense_summary(project, start, end)
	pending_total = number(base.get("pending_accounts", {}).get("total_hnl"))
	projection = number(Decimal(str(source_totals["closing_available_hnl"])) - Decimal(str(pending_total)))
	unreconciled_filters: dict[str, Any] = {
		"status": ["!=", "Draft"],
		"source_date": ["<=", end],
		"reconciliation_status": ["!=", "Reconciled"],
	}
	if project:
		unreconciled_filters["project"] = project
	base["analytics"] = {
		"rows": source_page["rows"],
		"expense_rows": expense_page["rows"],
		"contracts": contract_page["rows"],
		"source_pagination": source_page["pagination"],
		"expense_pagination": expense_page["pagination"],
		"contract_pagination": contract_page["pagination"],
		"source_totals": source_totals,
		"contract_totals": contract_totals,
		"contract_count": contract_totals["contract_count"],
		"income_by_channel": _income_by_channel(project, start, end),
		"critical_inventory": _critical_inventory(project),
		"unreconciled_count": frappe.db.count("NXR Fund Source", filters=unreconciled_filters),
		**expense_summary,
	}
	base["executive"] = {
		"received_hnl": source_totals["received_hnl"],
		"spent_hnl": source_totals["spent_hnl"],
		"paid_hnl": contract_totals["paid_hnl"],
		"cash_available_hnl": source_totals["closing_available_hnl"],
		"committed_hnl": number(base.get("budgets", {}).get("total_committed_hnl")),
		"budget_available_hnl": number(base.get("budgets", {}).get("total_available_hnl")),
		"projected_available_hnl": projection,
		"financial_percent": number(base.get("budgets", {}).get("utilization_percent")),
	}
	base["period"] = {"from_date": start, "to_date": end}
	return base
