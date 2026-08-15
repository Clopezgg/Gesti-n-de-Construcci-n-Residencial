from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe

from nexora.dashboard.service import (
	_alerts,
	_count,
	_get_all,
	_photo_urls,
	_project_context,
	_project_filters,
)

OPERATIONAL_ROW_LIMIT = 25
EVIDENCE_ROW_LIMIT = 8
RECENT_OPERATION_LIMIT = 10
CONTRACT_ROW_LIMIT = 6
POSTED_OPERATION_STATUSES = {
	"Executed",
	"Cancelled",
	"Compensated Partial",
	"Compensated Total",
}
VOIDED_OPERATION_STATUSES = {"Cancelled", "Compensated Total"}


def _progress_summary(project: str | None, period_end: str) -> dict[str, Any]:
	filters: dict[str, Any] = {
		**_project_filters(project),
		"status": ["!=", "Cancelled"],
		"recorded_date": ["<=", period_end],
	}
	records = _get_all(
		"NXR Progress Record",
		fields=[
			"name",
			"document_number",
			"status",
			"project",
			"phase",
			"description",
			"progress_percent",
			"recorded_date",
			"photos",
		],
		filters=filters,
		order_by="recorded_date desc, creation desc",
		limit=OPERATIONAL_ROW_LIMIT,
	)
	approved = next((row for row in records if row.get("status") == "Approved"), None)
	photos: list[str] = []
	for record in records:
		for url in _photo_urls(record.get("photos")):
			if url not in photos:
				photos.append(url)
	return {
		"physical_percent": float(approved.get("progress_percent") or 0) if approved else 0,
		"latest": approved,
		"record_count": int(frappe.db.count("NXR Progress Record", filters=filters)),
		"pending_review_count": sum(1 for row in records if row.get("status") == "Submitted"),
		"photos": photos[:EVIDENCE_ROW_LIMIT],
		"operational": {
			"active_contracts": _count(
				"NXR Contract",
				{**_project_filters(project), "status": ["in", ["Active", "Suspended", "In Liquidation"]]},
			),
			"pending_requests": _count(
				"NXR Purchase Request",
				{
					**_project_filters(project),
					"status": ["in", ["Draft", "Submitted", "In Review", "Pending Approval"]],
				},
			),
			"open_orders": _count(
				"NXR Purchase Order",
				{**_project_filters(project), "status": ["in", ["Draft", "Confirmed", "Approved", "Sent"]]},
			),
			"open_quality_issues": _count(
				"NXR Quality Check",
				{**_project_filters(project), "status": ["in", ["Open", "Failed"]]},
			),
		},
		"basis": {
			"physical": "Último avance aprobado con fecha igual o anterior al corte.",
			"operational": "Los conteos operativos reflejan el estado vigente al consultar.",
		},
	}


def _evidence_summary(project: str | None, period_end: str) -> dict[str, Any]:
	filters: dict[str, Any] = {
		**_project_filters(project),
		"status": ["!=", "Superseded"],
		"uploaded_at": ["<=", f"{period_end} 23:59:59"],
	}
	items = _get_all(
		"NXR Evidence",
		fields=[
			"name",
			"document_number",
			"status",
			"project",
			"evidence_kind",
			"channel",
			"file_url",
			"file_name",
			"mime_type",
			"uploaded_at",
			"uploaded_by",
		],
		filters=filters,
		order_by="uploaded_at desc, creation desc",
		limit=EVIDENCE_ROW_LIMIT,
	)
	pending_filters = {
		**_project_filters(project),
		"status": "Uploaded",
		"uploaded_at": ["<=", f"{period_end} 23:59:59"],
	}
	return {
		"count": _count("NXR Evidence", filters),
		"pending_review_count": _count("NXR Evidence", pending_filters),
		"items": items,
		"basis": "Evidencias registradas hasta la fecha de corte; su estado de revisión es el vigente.",
	}


def _operation_source_channels(operation_names: list[str]) -> dict[str, list[str]]:
	if not operation_names:
		return {}
	effects = _get_all(
		"NXR Operation Effect",
		fields=["operation", "fund_source", "creation", "name"],
		filters={"operation": ["in", operation_names]},
		order_by="creation asc, name asc",
		limit=RECENT_OPERATION_LIMIT * 20,
	)
	source_names = sorted({str(row.get("fund_source")) for row in effects if row.get("fund_source")})
	if not source_names:
		return {}
	sources = _get_all(
		"NXR Fund Source",
		fields=["name", "channel"],
		filters={"name": ["in", source_names]},
		limit=len(source_names),
	)
	channel_by_source = {str(row["name"]): str(row.get("channel") or "Other") for row in sources}
	channels_by_operation: dict[str, list[str]] = {}
	for effect in effects:
		operation = str(effect.get("operation") or "")
		channel = channel_by_source.get(str(effect.get("fund_source") or ""))
		if not operation or not channel:
			continue
		operation_channels = channels_by_operation.setdefault(operation, [])
		if channel not in operation_channels:
			operation_channels.append(channel)
	return channels_by_operation


def _operation_presentation(row: Mapping[str, Any], channels: list[str]) -> dict[str, Any]:
	operation_type = str(row.get("operation_type") or "")
	status = str(row.get("status") or "")
	is_reversal = operation_type == "Analytic Adjustment" and bool(row.get("reversal_of"))
	is_voided = is_reversal or status in VOIDED_OPERATION_STATUSES
	if is_reversal:
		kind = "Cancellation"
	elif operation_type == "Inflow":
		kind = "Income"
	elif operation_type == "Outflow":
		kind = "Expense"
	else:
		kind = operation_type or "Other"
	if is_voided:
		tone = "voided"
	elif kind == "Income":
		tone = "income"
	elif kind == "Expense":
		tone = "expense"
	else:
		tone = "neutral"
	return {
		**dict(row),
		"presentation_kind": kind,
		"presentation_status": "Posted" if status in POSTED_OPERATION_STATUSES else status,
		"presentation_tone": tone,
		"presentation_struck": is_voided,
		"source_channel": channels[0] if channels else None,
		"source_channels": channels,
	}


def _recent_operations(project: str | None, period_start: str, period_end: str) -> list[dict[str, Any]]:
	filters: dict[str, Any] = {
		**_project_filters(project),
		"operation_date": ["between", [period_start, period_end]],
		"status": ["!=", "Draft"],
	}
	rows = _get_all(
		"NXR Operation",
		fields=[
			"name",
			"document_number",
			"operation_type",
			"operation_code",
			"amount_hnl",
			"status",
			"operation_date",
			"payment_method",
			"reference_doctype",
			"reference_name",
			"reversal_of",
			"creation",
		],
		filters=filters,
		order_by="operation_date desc, creation desc",
		limit=RECENT_OPERATION_LIMIT,
	)
	channels = _operation_source_channels([str(row["name"]) for row in rows])
	return [_operation_presentation(row, channels.get(str(row["name"]), [])) for row in rows]


def build_operational_sections(
	*,
	project: str | None,
	period_start: str,
	period_end: str,
	finance: Mapping[str, Any],
	budgets: Mapping[str, Any],
	pending: Mapping[str, Any],
	contract_rows: list[dict[str, Any]],
	contract_count: int,
) -> dict[str, Any]:
	"""Compose the dashboard shell with bounded operational queries only."""
	progress = _progress_summary(project, period_end)
	evidence = _evidence_summary(project, period_end)
	contracts = {
		"active_count": int(contract_count),
		"items": contract_rows[:CONTRACT_ROW_LIMIT],
		"basis": "Contratos que intersectan el período seleccionado; importes según su estado vigente.",
	}
	return {
		"context": _project_context(project),
		"generated_at": frappe.utils.now_datetime(),
		"finance": dict(finance),
		"budgets": dict(budgets),
		"pending_accounts": dict(pending),
		"progress": progress,
		"evidence": evidence,
		"contracts": contracts,
		"alerts": _alerts(project, finance, budgets, pending, progress, evidence),
		"recent_operations": _recent_operations(project, period_start, period_end),
	}
