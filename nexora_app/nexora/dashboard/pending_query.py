from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.dashboard import query_utils
from nexora.dashboard.analytics_core import normalize_period, number
from nexora.permissions import require_project_access

MAX_PAGE_SIZE = 100


def _text(data: Mapping[str, Any], fieldname: str) -> str | None:
	return query_utils.text(data, fieldname)


def pending_commitments(data: Mapping[str, Any]) -> dict[str, Any]:
	"""Return outstanding reserved commitments for the selected analytical dimensions."""
	project = _text(data, "project")
	require_project_access(project, action="view_reports")
	try:
		_start, end = normalize_period(data.get("from_date"), data.get("to_date"))
	except (TypeError, ValueError) as exc:
		frappe.throw(_(str(exc)))
		raise AssertionError from exc
	page = max(int(data.get("page") or 1), 1)
	page_size = min(max(int(data.get("page_size") or 8), 1), MAX_PAGE_SIZE)
	params: dict[str, Any] = {
		"end": end,
		"limit": page_size,
		"offset": (page - 1) * page_size,
		"project": project,
		"source": _text(data, "source"),
		"entity": _text(data, "entity"),
		"economic_category": _text(data, "economic_category"),
		"cost_center": _text(data, "cost_center"),
	}
	rows = frappe.db.sql(
		"""
		SELECT pending.*,
			CASE
				WHEN pending.due_date IS NULL THEN 'Sin vencimiento'
				WHEN pending.due_date<%(end)s THEN 'Vencida'
				WHEN pending.due_date<=DATE_ADD(%(end)s, INTERVAL 7 DAY) THEN 'Próxima'
				ELSE 'Pendiente'
			END due_state
		FROM (
			SELECT c.name,c.document_number,c.description title,c.beneficiary,
				c.expiry_date due_date,COALESCE(SUM(e.amount_hnl),0) amount_hnl
			FROM `tabNXR Operation Effect` e
			INNER JOIN `tabNXR Operation` o ON o.name=e.operation
			INNER JOIN `tabNXR Commitment` c ON c.name=e.commitment
			WHERE e.dimension='Reserved'
				AND e.commitment IS NOT NULL
				AND o.status NOT IN ('Draft','Cancelled')
				AND o.operation_date<=%(end)s
				AND (%(project)s IS NULL OR COALESCE(e.project,o.project)=%(project)s)
				AND (%(source)s IS NULL OR e.fund_source=%(source)s)
				AND (%(entity)s IS NULL OR c.beneficiary=%(entity)s)
				AND (
					%(economic_category)s IS NULL
					OR COALESCE(e.economic_category,c.economic_category)=%(economic_category)s
				)
				AND (%(cost_center)s IS NULL OR COALESCE(e.cost_center,c.cost_center)=%(cost_center)s)
			GROUP BY c.name,c.document_number,c.description,c.beneficiary,c.expiry_date
			HAVING amount_hnl>0
		) pending
		ORDER BY pending.due_date IS NULL,pending.due_date,pending.document_number
		LIMIT %(limit)s OFFSET %(offset)s
		""",
		params,
		as_dict=True,
	)
	totals = frappe.db.sql(
		"""
		SELECT COUNT(*) item_count,COALESCE(SUM(pending.amount_hnl),0) total_hnl,
			COALESCE(SUM(CASE
				WHEN pending.due_date IS NOT NULL AND pending.due_date<%(end)s THEN 1 ELSE 0 END),0)
				overdue_count
		FROM (
			SELECT c.name,c.expiry_date due_date,COALESCE(SUM(e.amount_hnl),0) amount_hnl
			FROM `tabNXR Operation Effect` e
			INNER JOIN `tabNXR Operation` o ON o.name=e.operation
			INNER JOIN `tabNXR Commitment` c ON c.name=e.commitment
			WHERE e.dimension='Reserved'
				AND e.commitment IS NOT NULL
				AND o.status NOT IN ('Draft','Cancelled')
				AND o.operation_date<=%(end)s
				AND (%(project)s IS NULL OR COALESCE(e.project,o.project)=%(project)s)
				AND (%(source)s IS NULL OR e.fund_source=%(source)s)
				AND (%(entity)s IS NULL OR c.beneficiary=%(entity)s)
				AND (
					%(economic_category)s IS NULL
					OR COALESCE(e.economic_category,c.economic_category)=%(economic_category)s
				)
				AND (%(cost_center)s IS NULL OR COALESCE(e.cost_center,c.cost_center)=%(cost_center)s)
			GROUP BY c.name,c.expiry_date
			HAVING amount_hnl>0
		) pending
		""",
		params,
		as_dict=True,
	)[0]
	items = [
		{
			"doctype": "NXR Commitment",
			**dict(row),
			"amount_hnl": number(row.amount_hnl),
		}
		for row in rows
	]
	return {
		"count": int(totals.item_count or 0),
		"total_hnl": number(totals.total_hnl),
		"overdue_count": int(totals.overdue_count or 0),
		"items": items,
		"upcoming": [row for row in items if row.get("due_state") in {"Vencida", "Próxima"}][:6],
		"pagination": {
			"page": page,
			"page_size": page_size,
			"total": int(totals.item_count or 0),
		},
		"basis": "Reserva pendiente del Libro Central al final del período y dimensiones seleccionadas.",
	}
