from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

MONEY_QUANTUM = Decimal("0.01")
PERIOD_MIN = date(1900, 1, 1)
PERIOD_MAX = date(9999, 12, 31)


def money(value: object) -> Decimal:
	return Decimal(str(value or 0)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def number(value: object) -> float:
	return float(money(value))


def normalize_period(from_date: object = None, to_date: object = None) -> tuple[str, str]:
	start = _date(from_date) if from_date else PERIOD_MIN
	end = _date(to_date) if to_date else PERIOD_MAX
	if end < start:
		raise ValueError("La fecha final no puede ser anterior a la fecha inicial.")
	return start.isoformat(), end.isoformat()


def classify_effect(
	operation_type: object,
	dimension: object,
	amount_hnl: object,
	is_reversal: object = False,
) -> str:
	operation = str(operation_type or "")
	dimension_name = str(dimension or "")
	amount = money(amount_hnl)
	if str(is_reversal or "0").strip().lower() in {"1", "true", "yes"}:
		return "reversed"
	if dimension_name == "Reserved":
		return "reserved" if amount >= 0 else "released"
	if dimension_name != "Funds":
		return "analytic"
	if operation == "Inflow":
		return "received"
	if operation in {"Outflow", "Commitment Execution"}:
		return "spent"
	if operation == "Internal Transfer":
		return "transfer_in" if amount >= 0 else "transfer_out"
	if operation == "Real Return":
		return "returned"
	return "fund_adjustment"


def summarize_effect_rows(
	rows: Iterable[Mapping[str, Any]],
	*,
	from_date: object = None,
	to_date: object = None,
) -> dict[str, dict[str, float]]:
	start_text, end_text = normalize_period(from_date, to_date)
	start = _date(start_text)
	end = _date(end_text)
	buckets: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
	for row in rows:
		source = str(row.get("fund_source") or "")
		if not source:
			continue
		movement_date = _date(row.get("operation_date"))
		amount = money(row.get("amount_hnl"))
		dimension = str(row.get("dimension") or "")
		category = classify_effect(
			row.get("operation_type"),
			dimension,
			amount,
			row.get("is_reversal"),
		)
		if dimension == "Funds":
			buckets[source]["current_funds_hnl"] += amount
		elif dimension == "Reserved":
			buckets[source]["current_reserved_hnl"] += amount
		if movement_date < start:
			if dimension == "Funds":
				buckets[source]["opening_funds_hnl"] += amount
			elif dimension == "Reserved":
				buckets[source]["opening_reserved_hnl"] += amount
		if movement_date <= end:
			if dimension == "Funds":
				buckets[source]["closing_funds_hnl"] += amount
			elif dimension == "Reserved":
				buckets[source]["closing_reserved_hnl"] += amount
		if not start <= movement_date <= end:
			continue
		buckets[source][f"{category}_hnl"] += abs(amount)
		if dimension == "Funds":
			buckets[source]["period_funds_delta_hnl"] += amount
		elif dimension == "Reserved":
			buckets[source]["period_reserved_delta_hnl"] += amount

	result: dict[str, dict[str, float]] = {}
	for source, values in buckets.items():
		closing_funds = values["closing_funds_hnl"]
		closing_reserved = values["closing_reserved_hnl"]
		current_funds = values["current_funds_hnl"]
		current_reserved = values["current_reserved_hnl"]
		values["closing_available_hnl"] = closing_funds - closing_reserved
		values["current_available_hnl"] = current_funds - current_reserved
		result[source] = {key: number(value) for key, value in values.items()}
	return result


def stable_payload_hash(payload: Mapping[str, Any]) -> str:
	serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
	return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _date(value: object) -> date:
	if isinstance(value, date):
		return value
	return date.fromisoformat(str(value)[:10])
