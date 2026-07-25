from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any


def money(value: object) -> Decimal:
	try:
		d = Decimal(str(value))
	except (ValueError, TypeError, ArithmeticError):
		raise ValueError(f"Cannot convert {value!r} to Decimal")
	return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def reconcile_amounts(
	operations: list[dict[str, Any]],
) -> dict[str, Decimal]:
	total_inflows = Decimal(0)
	total_outflows = Decimal(0)
	count = 0
	for op in operations:
		amt = money(op.get("amount_hnl", 0))
		op_type = (op.get("operation_type") or "").strip()
		if op_type in ("Inflow", "Real Return"):
			total_inflows += amt
		elif op_type in ("Outflow", "Commitment Reserve", "Commitment Execution"):
			total_outflows += amt
		count += 1
	return {
		"total_inflows": total_inflows,
		"total_outflows": total_outflows,
		"net_flow": total_inflows - total_outflows,
		"operation_count": money(count),
	}


def format_statement_rows(
	rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
	result = []
	running_balance = Decimal(0)
	for row in rows:
		amount = money(row.get("amount_hnl", 0))
		op_type = (row.get("operation_type") or "").strip()
		if op_type in ("Inflow", "Real Return"):
			running_balance += amount
		elif op_type in ("Outflow", "Commitment Reserve", "Commitment Execution"):
			running_balance -= amount
		result.append(
			{
				"document_number": row.get("document_number", ""),
				"date": row.get("creation", ""),
				"operation_type": op_type,
				"amount_hnl": amount,
				"running_balance": money(running_balance),
				"status": row.get("status", ""),
				"description": row.get("description", ""),
			}
		)
	return result
