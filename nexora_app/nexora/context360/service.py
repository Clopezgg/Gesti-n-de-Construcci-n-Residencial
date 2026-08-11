from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.dashboard.executive import get_executive_snapshot
from nexora.permissions import require_project_access
from nexora.purchases.order_service import list_orders
from nexora.purchases.request_service import list_purchase_requests

# NXR-UX-0010 — Contexto 360° del proyecto.
#
# Esta función NO recalcula nada financiero: compone datos que ya producen otras
# funciones existentes y probadas (Capítulo 26 de la misión — "capa de comprensión
# sobre el dominio existente"). El grueso de la respuesta (finanzas, presupuesto,
# contratos, avance, evidencia, alertas, inventario crítico, actividad reciente) viene
# íntegro de `dashboard.executive.get_executive_snapshot`, que ya es la función real
# que usa `nexora_dashboard.js` — no una alternativa, la misma. Lo único que se agrega
# aquí es lo que esa función no cubre: la lista de compras abiertas (no solo el
# conteo que ya trae `progress.operational`) y los contratistas/proveedores
# distintos que aparecen en esos mismos contratos y órdenes ya obtenidos — sin
# ninguna consulta ni cálculo financiero nuevo.

OPEN_REQUEST_STATUSES = {"Draft", "Submitted", "In Review", "Approved"}
OPEN_ORDER_STATUSES = {"Draft", "Confirmed", "Approved", "Sent"}


def _payload(value: str | Mapping[str, Any]) -> dict[str, Any]:
	data = dict(value) if isinstance(value, Mapping) else frappe.parse_json(value)
	if not isinstance(data, dict):
		frappe.throw(_("El payload debe enviarse como un objeto JSON."))
	return data


def _project_field(data: Mapping[str, Any]) -> str:
	project = str(data.get("project") or "").strip()
	if not project:
		frappe.throw(_("Seleccione un proyecto para ver su contexto."))
	return project


def _project_basics(project: str) -> dict[str, Any]:
	doc = frappe.get_doc("Project", project)
	return {
		"name": doc.name,
		"project_name": doc.project_name,
		"status": doc.status,
		"expected_start_date": doc.get("expected_start_date"),
		"expected_end_date": doc.get("expected_end_date"),
		"percent_complete": doc.get("percent_complete"),
	}


def _open_purchase_requests(project: str, limit: int = 10) -> list[dict[str, Any]]:
	rows = list_purchase_requests(project=project, limit=50)
	open_rows = [row for row in rows if row.get("status") in OPEN_REQUEST_STATUSES]
	return open_rows[:limit]


def _open_purchase_orders(project: str, limit: int = 10) -> list[dict[str, Any]]:
	rows = list_orders(project=project, limit=50)
	open_rows = [row for row in rows if row.get("status") in OPEN_ORDER_STATUSES]
	return open_rows[:limit]


def _participants(contracts: list[dict[str, Any]], orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
	"""Contratistas/proveedores que participan, tomados de filas ya obtenidas — no es
	una consulta nueva al directorio, solo deduplica lo que contratos/órdenes ya traen.
	"""
	seen: dict[str, dict[str, Any]] = {}
	for row in contracts:
		name = str(row.get("contractor") or "").strip()
		if not name or name in seen:
			continue
		seen[name] = {
			"entity": name,
			"label": row.get("contractor_label") or name,
			"role": "contractor",
			"source": "NXR Contract",
		}
	for row in orders:
		name = str(row.get("supplier_entity") or "").strip()
		if not name or name in seen:
			continue
		seen[name] = {
			"entity": name,
			"label": row.get("supplier_profile") or name,
			"role": "supplier",
			"source": "NXR Purchase Order",
		}
	return list(seen.values())


@frappe.whitelist(methods=["POST"])
def get_project_overview(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Contexto 360° de un proyecto: resumen ejecutivo, salud financiera, presupuesto,
	fondos, contratos, compras abiertas, inventario crítico, avance/evidencia y
	alertas — todo proveniente de fuentes ya existentes y verificables, ninguna cifra
	calculada de forma independiente en esta función.
	"""
	data = _payload(payload)
	project = _project_field(data)
	# Único punto de control de acceso de esta función: si el proyecto no está
	# autorizado para el usuario actual, nada de lo demás se ejecuta. Reutiliza la
	# misma regla que ya protege el panel ejecutivo (`snapshot_query.py`) y la
	# búsqueda consolidada (`permissions.py`) — no una comprobación nueva.
	require_project_access(project, action="view_reports")

	snapshot = get_executive_snapshot({"project": project})
	contracts_items = list(snapshot.get("contracts", {}).get("items", []))
	open_requests = _open_purchase_requests(project)
	open_orders = _open_purchase_orders(project)

	return {
		"project": _project_basics(project),
		"context": snapshot.get("context"),
		"generated_at": frappe.utils.now_datetime(),
		"finance": snapshot.get("finance"),
		"budgets": snapshot.get("budgets"),
		"executive": snapshot.get("executive"),
		"pending_accounts": snapshot.get("pending_accounts"),
		"contracts": snapshot.get("contracts"),
		"progress": snapshot.get("progress"),
		"evidence": snapshot.get("evidence"),
		"alerts": snapshot.get("alerts"),
		"compliance_alerts": snapshot.get("compliance_alerts"),
		"recent_operations": snapshot.get("recent_operations"),
		"critical_inventory": snapshot.get("analytics", {}).get("critical_inventory", []),
		"open_purchases": {
			"requests": open_requests,
			"orders": open_orders,
			"count": len(open_requests) + len(open_orders),
		},
		"participants": _participants(contracts_items, open_orders),
	}
