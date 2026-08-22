"""Serie temporal real de flujo de fondos (últimos 6 meses) para el panel
ejecutivo. Reutiliza `source_query.source_totals` — la misma consulta ya
auditada que usa `_filtered_source_totals`/`aggregate_source_totals` en
`snapshot_query.py` — llamada una vez por mes en vez de reescribir su SQL.
"""

from __future__ import annotations

import calendar
from datetime import date
from typing import Any

import frappe

from nexora.dashboard.source_query import source_totals

MONTHS_WINDOW = 6


def _month_bounds(end_date: date, months_back: int) -> tuple[str, str]:
	year = end_date.year
	month = end_date.month - months_back
	while month <= 0:
		month += 12
		year -= 1
	last_day = calendar.monthrange(year, month)[1]
	start = date(year, month, 1)
	end = date(year, month, last_day)
	if months_back == 0:
		end = min(end, end_date)
	return start.isoformat(), end.isoformat()


def monthly_cash_flow(project: str | None, period_end: str) -> list[dict[str, Any]]:
	end_date = frappe.utils.getdate(period_end)
	rows: list[dict[str, Any]] = []
	for offset in range(MONTHS_WINDOW - 1, -1, -1):
		start, end = _month_bounds(end_date, offset)
		totals = source_totals(project, start, end)
		rows.append(
			{
				"month": start[:7],
				"income_hnl": totals["net_received_hnl"],
				"expense_hnl": totals["spent_hnl"],
				"balance_hnl": totals["closing_available_hnl"],
			}
		)
	return rows
