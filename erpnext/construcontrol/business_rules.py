from __future__ import annotations

import unicodedata
from typing import Any


def normalize_text(value: Any) -> str:
	text = unicodedata.normalize("NFKD", str(value or ""))
	return " ".join("".join(char for char in text if not unicodedata.combining(char)).casefold().split())


def normalize_income_channel(value: Any) -> str:
	raw = normalize_text(value)
	aliases = {
		"remesa": "remittance",
		"remittance": "remittance",
		"deposito": "deposit",
		"deposit": "deposit",
		"transferencia": "transfer",
		"transfer": "transfer",
		"efectivo": "cash",
		"cash": "cash",
		"otro": "other",
		"other": "other",
	}
	return aliases.get(raw, "other")


def funding_amounts(
	gross_amount: Any,
	fee_amount: Any = 0,
	currency: Any = "HNL",
	exchange_rate: Any = 1,
) -> dict[str, float | str]:
	"""Return one canonical FI01 conversion from original currency to HNL."""
	gross = float(gross_amount or 0)
	fee = float(fee_amount or 0)
	if gross < 0 or fee < 0:
		raise ValueError("El monto y la comisión no pueden ser negativos.")
	if fee > gross:
		raise ValueError("La comisión no puede superar el monto bruto.")

	original_currency = str(currency or "HNL").strip().upper() or "HNL"
	rate = 1.0 if original_currency == "HNL" else float(exchange_rate or 0)
	if rate <= 0:
		raise ValueError("El tipo de cambio debe ser mayor que cero.")

	net = gross - fee
	return {
		"gross": round(gross, 6),
		"fee": round(fee, 6),
		"net": round(net, 6),
		"currency": original_currency,
		"exchange_rate": round(rate, 6),
		"net_hnl": round(net * rate, 2),
	}


def normalize_expense_state(raw_state: Any, amount: Any, paid_amount: Any = 0) -> dict[str, float | str]:
	"""Normalize explicit payment evidence without guessing that an unknown row was paid."""
	state = normalize_text(raw_state).replace(" ", "_")
	total = max(float(amount or 0), 0.0)
	paid = min(max(float(paid_amount or 0), 0.0), total)

	if state == "paid":
		return {"payment_status": "paid", "approval_status": "approved", "paid": total, "balance": 0.0}
	if state in {"partially_paid", "partial"}:
		return {
			"payment_status": "partially_paid",
			"approval_status": "approved",
			"paid": paid,
			"balance": max(total - paid, 0.0),
		}
	if state == "overdue":
		return {
			"payment_status": "overdue",
			"approval_status": "approved",
			"paid": paid,
			"balance": max(total - paid, 0.0),
		}
	if state == "approved":
		return {
			"payment_status": "approved",
			"approval_status": "approved",
			"paid": paid,
			"balance": max(total - paid, 0.0),
		}
	if state in {"cancelled", "canceled", "reimbursed"}:
		canonical = "cancelled" if state in {"cancelled", "canceled"} else "reimbursed"
		return {"payment_status": canonical, "approval_status": "draft", "paid": 0.0, "balance": 0.0}
	if state in {"pending", "pending_approval"}:
		return {
			"payment_status": "pending_approval",
			"approval_status": "pending",
			"paid": paid,
			"balance": max(total - paid, 0.0),
		}
	return {
		"payment_status": "draft",
		"approval_status": "draft",
		"paid": paid,
		"balance": max(total - paid, 0.0),
	}


def expense_amounts(
	amount: Any,
	payment_status: Any,
	financial_status: Any,
	paid_amount: Any = 0,
	balance_due: Any = 0,
	approval_status: Any = "approved",
) -> tuple[float, float, float]:
	"""Return approved cost, paid cash and outstanding balance consistently."""
	total = max(float(amount or 0), 0.0)
	payment = normalize_text(payment_status).replace(" ", "_")
	financial = normalize_text(financial_status).replace(" ", "_")
	approval = normalize_text(approval_status).replace(" ", "_")
	if (
		approval == "rejected"
		or payment in {"cancelled", "canceled", "reimbursed"}
		or financial in {"cancelled", "canceled", "reimbursed"}
	):
		return 0.0, 0.0, 0.0

	paid = min(max(float(paid_amount or 0), 0.0), total)
	balance = max(float(balance_due or 0), 0.0)
	if payment == "paid":
		paid = total if paid <= 0 else paid
		balance = 0.0
	elif payment in {"partially_paid", "partial"}:
		balance = balance or max(total - paid, 0.0)
	elif payment in {"", "draft"} and financial == "paid":
		paid = total if paid <= 0 else paid
		balance = 0.0
	elif balance <= 0:
		balance = max(total - paid, 0.0)

	if approval in {"", "draft", "pending"} and payment not in {
		"paid",
		"partially_paid",
		"partial",
		"overdue",
		"approved",
	}:
		return 0.0, 0.0, 0.0
	return total, paid, balance


__all__ = [
	"expense_amounts",
	"funding_amounts",
	"normalize_expense_state",
	"normalize_income_channel",
	"normalize_text",
]
