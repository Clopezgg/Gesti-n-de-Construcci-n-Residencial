from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.context360.core import (
	CATEGORY_LABELS,
	MAX_LIMIT,
	OPERATION_TYPE_LABELS,
	PER_SOURCE_FETCH_MULTIPLIER,
	STOCK_TRANSACTION_LABELS,
	clamp_limit,
	normalize_event,
	resolve_categories,
	sort_and_truncate,
)
from nexora.permissions import require_project_access

# NXR-UX-0011 — Timeline universal del proyecto.
#
# No existía ninguna función que unificara la historia de un proyecto a través de
# los documentos reales que ya existen. Esta no es una bitácora nueva ni un ledger
# paralelo: lee los mismos documentos de negocio que cada pantalla ya lee (NXR
# Operation, NXR Commitment, órdenes/recepciones de compra, contratos y sus
# adendas/estimaciones, movimientos de inventario, avance, evidencia), normaliza su
# forma (`context360.core.normalize_event`) para poder ordenarlos juntos por fecha,
# y nada más. Ningún evento se inventa: si un documento no tiene fecha utilizable no
# aparece, en vez de fabricarle una.
#
# Permisos: cada consulta usa `frappe.get_list` (no `frappe.get_all`), que sí aplica
# las reglas de permiso de Frappe por fila; además toda la función está cerrada por
# `require_project_access` antes de tocar cualquier doctype, igual que el resto de
# `context360`. Un usuario sin acceso al proyecto no llega a ejecutar ninguna consulta.


def _payload(value: str | Mapping[str, Any]) -> dict[str, Any]:
	return dict(value) if isinstance(value, Mapping) else frappe.parse_json(value)


def _fetch(doctype: str, filters: dict[str, Any], fields: list[str], limit: int) -> list[dict[str, Any]]:
	try:
		return list(
			frappe.get_list(
				doctype,
				filters=filters,
				fields=fields,
				order_by="modified desc",
				limit_page_length=limit,
			)
		)
	except (frappe.DoesNotExistError, frappe.ValidationError, frappe.PermissionError):
		return []


def _financial_events(project: str, limit: int) -> list[dict[str, Any]]:
	events: list[dict[str, Any]] = []
	for row in _fetch(
		"NXR Operation",
		{"project": project},
		["name", "document_number", "operation_type", "operation_date", "amount_hnl", "status", "evidence",
			"executed_by", "approved_by", "requester"],
		limit,
	):
		op_type = str(row.get("operation_type") or "")
		event = normalize_event(
			category="financiero",
			doctype="NXR Operation",
			row=row,
			date_field="operation_date",
			title=OPERATION_TYPE_LABELS.get(op_type, op_type or "Operación"),
			actor_fields=("executed_by", "approved_by", "requester"),
			amount_field="amount_hnl",
		)
		if event:
			events.append(event)
	for row in _fetch(
		"NXR Commitment",
		{"project": project},
		["name", "document_number", "description", "commitment_date", "amount_hnl", "status", "evidence",
			"approved_by", "requester"],
		limit,
	):
		event = normalize_event(
			category="financiero",
			doctype="NXR Commitment",
			row=row,
			date_field="commitment_date",
			title=str(row.get("description") or "Compromiso"),
			actor_fields=("approved_by", "requester"),
			amount_field="amount_hnl",
		)
		if event:
			events.append(event)
	return events


def _purchase_events(project: str, limit: int) -> list[dict[str, Any]]:
	events: list[dict[str, Any]] = []
	for row in _fetch(
		"NXR Purchase Request",
		{"project": project},
		["name", "document_number", "request_date", "total_amount", "status", "evidence", "decided_by",
			"requested_by"],
		limit,
	):
		event = normalize_event(
			category="compras",
			doctype="NXR Purchase Request",
			row=row,
			date_field="request_date",
			title="Solicitud de compra",
			actor_fields=("decided_by", "requested_by"),
			amount_field="total_amount",
		)
		if event:
			events.append(event)
	for row in _fetch(
		"NXR Purchase Order",
		{"project": project},
		["name", "document_number", "order_date", "total_amount", "status", "evidence", "approved_by",
			"confirmed_by", "sent_by"],
		limit,
	):
		event = normalize_event(
			category="compras",
			doctype="NXR Purchase Order",
			row=row,
			date_field="order_date",
			title="Orden de compra",
			actor_fields=("approved_by", "confirmed_by", "sent_by"),
			amount_field="total_amount",
		)
		if event:
			events.append(event)
	for row in _fetch(
		"NXR Goods Receipt",
		{"project": project},
		["name", "document_number", "receipt_date", "total_amount", "status", "evidence", "received_by"],
		limit,
	):
		event = normalize_event(
			category="compras",
			doctype="NXR Goods Receipt",
			row=row,
			date_field="receipt_date",
			title="Recepción de mercancía",
			actor_fields=("received_by",),
			amount_field="total_amount",
		)
		if event:
			events.append(event)
	return events


def _contract_events(project: str, limit: int) -> list[dict[str, Any]]:
	events: list[dict[str, Any]] = []
	contracts = _fetch(
		"NXR Contract",
		{"project": project},
		["name", "document_number", "start_date", "current_amount", "status", "contractor"],
		limit,
	)
	for row in contracts:
		event = normalize_event(
			category="contratos",
			doctype="NXR Contract",
			row=row,
			date_field="start_date",
			title="Contrato",
			actor_fields=(),
			amount_field="current_amount",
		)
		if event:
			events.append(event)
	contract_names = [str(row["name"]) for row in contracts]
	if not contract_names:
		return events
	for row in _fetch(
		"NXR Contract Amendment",
		{"contract": ["in", contract_names]},
		["name", "document_number", "effective_date", "status", "evidence", "approved_by"],
		limit,
	):
		event = normalize_event(
			category="contratos",
			doctype="NXR Contract Amendment",
			row=row,
			date_field="effective_date",
			title="Adenda de contrato",
			actor_fields=("approved_by",),
			amount_field=None,
		)
		if event:
			events.append(event)
	for row in _fetch(
		"NXR Contract Estimate",
		{"contract": ["in", contract_names]},
		["name", "document_number", "period_end", "payable_amount", "status", "evidence", "approved_by",
			"requester"],
		limit,
	):
		event = normalize_event(
			category="contratos",
			doctype="NXR Contract Estimate",
			row=row,
			date_field="period_end",
			title="Estimación de contrato",
			actor_fields=("approved_by", "requester"),
			amount_field="payable_amount",
		)
		if event:
			events.append(event)
	return events


def _inventory_events(project: str, limit: int) -> list[dict[str, Any]]:
	events: list[dict[str, Any]] = []
	for row in _fetch(
		"NXR Stock Transaction",
		{"project": project},
		["name", "document_number", "transaction_type", "transaction_date", "total_amount", "status", "evidence"],
		limit,
	):
		kind = str(row.get("transaction_type") or "")
		event = normalize_event(
			category="inventario",
			doctype="NXR Stock Transaction",
			row=row,
			date_field="transaction_date",
			title=STOCK_TRANSACTION_LABELS.get(kind, kind or "Movimiento de inventario"),
			actor_fields=(),
			amount_field="total_amount",
		)
		if event:
			events.append(event)
	return events


def _progress_events(project: str, limit: int) -> list[dict[str, Any]]:
	events: list[dict[str, Any]] = []
	for row in _fetch(
		"NXR Progress Record",
		{"project": project},
		["name", "document_number", "phase", "description", "recorded_date", "progress_percent", "status",
			"responsible"],
		limit,
	):
		phase = str(row.get("phase") or "").strip()
		title = f"Avance{': ' + phase if phase else ''}"
		event = normalize_event(
			category="avance",
			doctype="NXR Progress Record",
			row=row,
			date_field="recorded_date",
			title=title,
			actor_fields=("responsible",),
			amount_field=None,
		)
		if event:
			events.append(event)
	return events


def _evidence_events(project: str, limit: int) -> list[dict[str, Any]]:
	events: list[dict[str, Any]] = []
	for row in _fetch(
		"NXR Evidence",
		{"project": project},
		["name", "document_number", "evidence_kind", "uploaded_at", "status", "uploaded_by"],
		limit,
	):
		kind = str(row.get("evidence_kind") or "").strip()
		event = normalize_event(
			category="evidencia",
			doctype="NXR Evidence",
			row={**row, "evidence": row.get("name")},
			date_field="uploaded_at",
			title=f"Evidencia{': ' + kind if kind else ''}",
			actor_fields=("uploaded_by",),
			amount_field=None,
		)
		if event:
			events.append(event)
	return events


CATEGORY_BUILDERS = {
	"financiero": _financial_events,
	"compras": _purchase_events,
	"contratos": _contract_events,
	"inventario": _inventory_events,
	"avance": _progress_events,
	"evidencia": _evidence_events,
}
assert set(CATEGORY_BUILDERS) == set(CATEGORY_LABELS)


@frappe.whitelist(methods=["POST"])
def get_project_timeline(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Historia cronológica real del proyecto, a partir de los documentos que ya
	existen. `categories` filtra qué fuentes consultar (por defecto, todas). No
	pagina por cursor de fecha todavía: cada fuente trae hasta el doble de filas del
	límite pedido y se corta el total combinado — documentado como límite conocido,
	no oculto, en `docs/nexora/MATRIZ_REQUISITOS.md`.
	"""
	data = _payload(payload)
	project = str(data.get("project") or "").strip()
	if not project:
		frappe.throw(_("Seleccione un proyecto para ver su historia."))
	require_project_access(project, action="view_reports")

	categories = resolve_categories(data.get("categories"), CATEGORY_BUILDERS)
	limit = clamp_limit(data.get("limit"))
	per_source_limit = min(limit * PER_SOURCE_FETCH_MULTIPLIER, MAX_LIMIT)

	events: list[dict[str, Any]] = []
	for category in categories:
		events.extend(CATEGORY_BUILDERS[category](project, per_source_limit))

	truncated, has_more = sort_and_truncate(events, limit)
	return {
		"project": project,
		"categories": categories,
		"events": truncated,
		"count": len(truncated),
		"has_more": has_more,
	}
