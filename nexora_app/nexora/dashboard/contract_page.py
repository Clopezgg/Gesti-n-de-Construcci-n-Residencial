from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe

from nexora.dashboard.analytics_core import number
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


def contract_page(data: Mapping[str, Any], *, default_size: int = DEFAULT_PAGE_SIZE) -> dict[str, Any]:
	project = resolve_project(data)
	start, end = resolve_period(data)
	page, page_size, offset = resolve_pagination(data, default_size)
	params: dict[str, Any] = {
		"start": start,
		"end": end,
		"limit": page_size,
		"offset": offset,
		"project": project,
		"contract": text(data, "contract"),
		"contractor": text(data, "contractor"),
		"contract_status": text(data, "contract_status"),
	}
	rows = frappe.db.sql(
		"""
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
		WHERE c.status!='Cancelled Before Active'
			AND c.start_date<=%(end)s
			AND (c.current_end_date IS NULL OR c.current_end_date>=%(start)s)
			AND (%(project)s IS NULL OR c.project=%(project)s)
			AND (%(contract)s IS NULL OR c.name=%(contract)s)
			AND (%(contractor)s IS NULL OR c.contractor=%(contractor)s)
			AND (%(contract_status)s IS NULL OR c.status=%(contract_status)s)
		ORDER BY c.start_date DESC,c.modified DESC
		LIMIT %(limit)s OFFSET %(offset)s
		""",
		params,
		as_dict=True,
	)
	count = frappe.db.sql(
		"""
		SELECT COUNT(*) FROM `tabNXR Contract` c
		WHERE c.status!='Cancelled Before Active'
			AND c.start_date<=%(end)s
			AND (c.current_end_date IS NULL OR c.current_end_date>=%(start)s)
			AND (%(project)s IS NULL OR c.project=%(project)s)
			AND (%(contract)s IS NULL OR c.name=%(contract)s)
			AND (%(contractor)s IS NULL OR c.contractor=%(contractor)s)
			AND (%(contract_status)s IS NULL OR c.status=%(contract_status)s)
		""",
		params,
	)[0][0]
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
