from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

import frappe
from frappe import _

from nexora.dashboard.analytics_core import net_received_amount, number
from nexora.dashboard.query_utils import (
	DEFAULT_PAGE_SIZE,
	text,
)
from nexora.dashboard.query_utils import (
	pagination as resolve_pagination,
)
from nexora.dashboard.query_utils import (
	period as resolve_period,
)
from nexora.dashboard.query_utils import (
	project as resolve_project,
)


def _income_totals(values: Mapping[str, Any]) -> dict[str, Any]:
	result = dict(values)
	result["gross_received_hnl"] = number(result.get("received_hnl"))
	result["reversed_inflow_hnl"] = number(result.get("reversed_inflow_hnl"))
	result["net_received_hnl"] = net_received_amount(
		result["gross_received_hnl"], result["reversed_inflow_hnl"]
	)
	return result


def source_effect_aggregates(source_names: list[str], start: str, end: str) -> dict[str, dict[str, Any]]:
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
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND COALESCE(e.is_reversal,0)=0 AND e.dimension='Funds' AND o.operation_type='Inflow' AND e.amount_hnl>0 THEN e.amount_hnl ELSE 0 END),0) received_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND COALESCE(e.is_reversal,0)=1 AND e.dimension='Funds' AND reversed_effect.effect_type='Received' THEN ABS(e.amount_hnl) ELSE 0 END),0) reversed_inflow_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND COALESCE(e.is_reversal,0)=0 AND e.dimension='Funds' AND o.operation_type IN ('Outflow','Commitment Execution') AND e.amount_hnl<0 THEN -e.amount_hnl ELSE 0 END),0) spent_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND COALESCE(e.is_reversal,0)=0 AND e.dimension='Funds' AND o.operation_type='Internal Transfer' AND e.amount_hnl>0 THEN e.amount_hnl ELSE 0 END),0) transfer_in_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND COALESCE(e.is_reversal,0)=0 AND e.dimension='Funds' AND o.operation_type='Internal Transfer' AND e.amount_hnl<0 THEN -e.amount_hnl ELSE 0 END),0) transfer_out_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND COALESCE(e.is_reversal,0)=0 AND e.dimension='Funds' AND o.operation_type='Real Return' THEN ABS(e.amount_hnl) ELSE 0 END),0) returned_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND COALESCE(e.is_reversal,0)=1 THEN ABS(e.amount_hnl) ELSE 0 END),0) reversed_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND COALESCE(e.is_reversal,0)=0 AND e.dimension='Reserved' AND e.amount_hnl>0 THEN e.amount_hnl ELSE 0 END),0) reserved_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND COALESCE(e.is_reversal,0)=0 AND e.dimension='Reserved' AND e.amount_hnl<0 THEN -e.amount_hnl ELSE 0 END),0) released_hnl
		FROM `tabNXR Operation Effect` e
		INNER JOIN `tabNXR Operation` o ON o.name=e.operation
		LEFT JOIN `tabNXR Operation Effect` reversed_effect ON reversed_effect.name=e.reverses_effect
		WHERE e.fund_source IN %(sources)s AND o.status NOT IN ('Draft','Cancelled')
		GROUP BY e.fund_source
		""",
		{"sources": tuple(source_names), "start": start, "end": end},
		as_dict=True,
	)
	return {str(row.fund_source): _income_totals(dict(row)) for row in rows}


def source_statement(
	data: Mapping[str, Any], *, default_page_size: int = DEFAULT_PAGE_SIZE
) -> dict[str, Any]:
	project = resolve_project(data)
	start, end = resolve_period(data)
	page, page_size, offset = resolve_pagination(data, default_page_size)
	filters: list[list[Any]] = [["status", "!=", "Draft"], ["source_date", "<=", end]]
	for fieldname, value in (
		("project", project),
		("name", text(data, "source")),
		("status", text(data, "source_status")),
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
	aggregates = source_effect_aggregates([str(row.name) for row in rows], start, end)
	statement = []
	for row in rows:
		values = aggregates.get(str(row.name), {})
		closing_funds = Decimal(str(values.get("closing_funds_hnl") or 0))
		closing_reserved = Decimal(str(values.get("closing_reserved_hnl") or 0))
		current_funds = Decimal(str(values.get("current_funds_hnl") or 0))
		current_reserved = Decimal(str(values.get("current_reserved_hnl") or 0))
		closing_available = closing_funds - closing_reserved
		statement.append(
			{
				**dict(row),
				**{key: number(value) for key, value in values.items() if key != "fund_source"},
				"closing_available_hnl": number(closing_available),
				"current_available_hnl": number(current_funds - current_reserved),
				"projected_hnl": number(closing_available),
				"projection_basis": "Saldo al cierre después de reservas; las obligaciones pendientes se informan por separado.",
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


def source_movement_page(data: Mapping[str, Any]) -> dict[str, Any]:
	project = resolve_project(data)
	start, end = resolve_period(data)
	page, page_size, offset = resolve_pagination(data)
	source = text(data, "source")
	if not source:
		frappe.throw(_("Seleccione una fuente para consultar sus movimientos."))
	params: dict[str, Any] = {
		"source": source,
		"project": project,
		"start": start,
		"end": end,
		"limit": page_size,
		"offset": offset,
	}
	rows = frappe.db.sql(
		"""
		SELECT e.name,e.operation,o.document_number,o.operation_date,o.operation_type,o.status,
			e.dimension,e.effect_type,e.amount_hnl,e.cost_center,e.economic_category,e.is_reversal,
			e.reverses_effect,e.correlation_id
		FROM `tabNXR Operation Effect` e
		INNER JOIN `tabNXR Operation` o ON o.name=e.operation
		WHERE e.fund_source=%(source)s
			AND o.operation_date BETWEEN %(start)s AND %(end)s
			AND o.status NOT IN ('Draft','Cancelled')
			AND (%(project)s IS NULL OR o.project=%(project)s)
		ORDER BY o.operation_date DESC,o.creation DESC,e.creation DESC
		LIMIT %(limit)s OFFSET %(offset)s
		""",
		params,
		as_dict=True,
	)
	count = frappe.db.sql(
		"""
		SELECT COUNT(*)
		FROM `tabNXR Operation Effect` e
		INNER JOIN `tabNXR Operation` o ON o.name=e.operation
		WHERE e.fund_source=%(source)s
			AND o.operation_date BETWEEN %(start)s AND %(end)s
			AND o.status NOT IN ('Draft','Cancelled')
			AND (%(project)s IS NULL OR o.project=%(project)s)
		""",
		params,
	)[0][0]
	return {
		"source": source,
		"rows": [{**dict(row), "amount_hnl": number(row.amount_hnl)} for row in rows],
		"pagination": {"page": page, "page_size": page_size, "total": int(count)},
		"period": {"from_date": start, "to_date": end},
	}


def source_totals(project: str | None, start: str, end: str) -> dict[str, float]:
	row = frappe.db.sql(
		"""
		SELECT
			COALESCE(SUM(CASE WHEN e.dimension='Funds' AND o.operation_date < %(start)s THEN e.amount_hnl ELSE 0 END),0) opening_funds_hnl,
			COALESCE(SUM(CASE WHEN e.dimension='Reserved' AND o.operation_date < %(start)s THEN e.amount_hnl ELSE 0 END),0) opening_reserved_hnl,
			COALESCE(SUM(CASE WHEN e.dimension='Funds' AND o.operation_date <= %(end)s THEN e.amount_hnl ELSE 0 END),0) closing_funds_hnl,
			COALESCE(SUM(CASE WHEN e.dimension='Reserved' AND o.operation_date <= %(end)s THEN e.amount_hnl ELSE 0 END),0) closing_reserved_hnl,
			COALESCE(SUM(CASE WHEN e.dimension='Funds' THEN e.amount_hnl ELSE 0 END),0) current_funds_hnl,
			COALESCE(SUM(CASE WHEN e.dimension='Reserved' THEN e.amount_hnl ELSE 0 END),0) current_reserved_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND COALESCE(e.is_reversal,0)=0 AND e.dimension='Funds' AND o.operation_type='Inflow' AND e.amount_hnl>0 THEN e.amount_hnl ELSE 0 END),0) received_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND COALESCE(e.is_reversal,0)=1 AND e.dimension='Funds' AND reversed_effect.effect_type='Received' THEN ABS(e.amount_hnl) ELSE 0 END),0) reversed_inflow_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND COALESCE(e.is_reversal,0)=0 AND e.dimension='Funds' AND o.operation_type IN ('Outflow','Commitment Execution') AND e.amount_hnl<0 THEN -e.amount_hnl ELSE 0 END),0) spent_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND COALESCE(e.is_reversal,0)=0 AND e.dimension='Funds' AND o.operation_type='Internal Transfer' AND e.amount_hnl>0 THEN e.amount_hnl ELSE 0 END),0) transfer_in_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND COALESCE(e.is_reversal,0)=0 AND e.dimension='Funds' AND o.operation_type='Internal Transfer' AND e.amount_hnl<0 THEN -e.amount_hnl ELSE 0 END),0) transfer_out_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND COALESCE(e.is_reversal,0)=0 AND e.dimension='Funds' AND o.operation_type='Real Return' THEN ABS(e.amount_hnl) ELSE 0 END),0) returned_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND COALESCE(e.is_reversal,0)=1 THEN ABS(e.amount_hnl) ELSE 0 END),0) reversed_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND COALESCE(e.is_reversal,0)=0 AND e.dimension='Reserved' AND e.amount_hnl>0 THEN e.amount_hnl ELSE 0 END),0) reserved_hnl,
			COALESCE(SUM(CASE WHEN o.operation_date BETWEEN %(start)s AND %(end)s AND COALESCE(e.is_reversal,0)=0 AND e.dimension='Reserved' AND e.amount_hnl<0 THEN -e.amount_hnl ELSE 0 END),0) released_hnl
		FROM `tabNXR Operation Effect` e
		INNER JOIN `tabNXR Operation` o ON o.name=e.operation
		LEFT JOIN `tabNXR Operation Effect` reversed_effect ON reversed_effect.name=e.reverses_effect
		WHERE o.status NOT IN ('Draft','Cancelled')
			AND (%(project)s IS NULL OR o.project=%(project)s)
		""",
		{"project": project, "start": start, "end": end},
		as_dict=True,
	)[0]
	result = _income_totals({key: number(value) for key, value in row.items()})
	for prefix in ("opening", "closing", "current"):
		result[f"{prefix}_available_hnl"] = number(
			Decimal(str(row.get(f"{prefix}_funds_hnl") or 0))
			- Decimal(str(row.get(f"{prefix}_reserved_hnl") or 0))
		)
	return result


def income_by_channel(project: str | None, start: str, end: str) -> list[dict[str, Any]]:
	rows = frappe.db.sql(
		"""
		SELECT totals.label,totals.amount_hnl
		FROM (
			SELECT COALESCE(s.channel,'Other') label,
				COALESCE(SUM(CASE
					WHEN COALESCE(e.is_reversal,0)=0 AND o.operation_type='Inflow' AND e.amount_hnl>0 THEN e.amount_hnl
					WHEN COALESCE(e.is_reversal,0)=1 AND reversed_effect.effect_type='Received' THEN e.amount_hnl
					ELSE 0
				END),0) amount_hnl
			FROM `tabNXR Operation Effect` e
			INNER JOIN `tabNXR Operation` o ON o.name=e.operation
			INNER JOIN `tabNXR Fund Source` s ON s.name=e.fund_source
			LEFT JOIN `tabNXR Operation Effect` reversed_effect ON reversed_effect.name=e.reverses_effect
			WHERE o.status NOT IN ('Draft','Cancelled') AND e.dimension='Funds'
				AND o.operation_date BETWEEN %(start)s AND %(end)s
				AND (%(project)s IS NULL OR o.project=%(project)s)
			GROUP BY s.channel
		) totals
		WHERE ABS(totals.amount_hnl) >= 0.005
		ORDER BY totals.amount_hnl DESC
		""",
		{"project": project, "start": start, "end": end},
		as_dict=True,
	)
	return [{"label": row.label, "amount_hnl": number(row.amount_hnl)} for row in rows]
