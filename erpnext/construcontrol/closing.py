from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any


def closing_snapshot(
	*,
	initial_balance: Any,
	income: Any,
	recognized_expense: Any,
	paid_expense: Any,
	pending_expense: Any,
	inventory_movements: Any = 0,
	progress_updates: Any = 0,
	quality_failures: Any = 0,
	open_approvals: Any = 0,
	unreconciled_funds: Any = 0,
) -> dict[str, Any]:
	initial = float(initial_balance or 0)
	received = float(income or 0)
	recognized = float(recognized_expense or 0)
	paid = float(paid_expense or 0)
	pending = float(pending_expense or 0)
	if min(received, recognized, paid, pending) < 0 or paid > recognized + 0.005:
		raise ValueError("Los montos del cierre semanal son inconsistentes.")
	pending_items: list[str] = []
	if pending:
		pending_items.append(f"Gastos pendientes por L {pending:,.2f}")
	if int(open_approvals or 0):
		pending_items.append(f"{int(open_approvals)} aprobación(es) pendiente(s)")
	if int(unreconciled_funds or 0):
		pending_items.append(f"{int(unreconciled_funds)} ingreso(s) sin conciliar")
	if int(quality_failures or 0):
		pending_items.append(f"{int(quality_failures)} incidencia(s) de calidad abierta(s)")
	status = "reconciled" if not pending_items else "pending"
	return {
		"initial_balance_hnl": round(initial, 2),
		"income_hnl": round(received, 2),
		"recognized_expense_hnl": round(recognized, 2),
		"expense_hnl": round(paid, 2),
		"pending_expense_hnl": round(pending, 2),
		"committed_hnl": round(pending, 2),
		"final_balance_hnl": round(initial + received - paid, 2),
		"projected_balance_hnl": round(initial + received - paid - pending, 2),
		"inventory_movement_count": int(inventory_movements or 0),
		"progress_update_count": int(progress_updates or 0),
		"quality_failure_count": int(quality_failures or 0),
		"reconciliation_status": status,
		"pending_items": pending_items,
	}


def snapshot_digest(snapshot: Mapping[str, Any]) -> str:
	payload = json.dumps(
		dict(snapshot), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
	)
	return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def resolve_repeat(existing_status: Any, existing_digest: Any, current_digest: Any) -> str:
	status = str(existing_status or "draft").strip().lower()
	if str(existing_digest or "") == str(current_digest or ""):
		return "reuse"
	if status == "draft":
		return "refresh"
	return "reopen_required"
