from __future__ import annotations

from collections.abc import Mapping
from typing import Any

# NXR-UX-0011 — lógica pura de la timeline universal, sin dependencia de Frappe
# (mismo principio que `purchases/receipt_core.py` o `budget/core.py`: lo que no
# necesita base de datos se puede probar por unidad de verdad, no solo declarar
# probado). `context360/timeline.py` hace las consultas reales y llama aquí para
# normalizar cada fila.

CATEGORY_LABELS = {
	"financiero": "Financiero",
	"compras": "Compras",
	"contratos": "Contratos",
	"inventario": "Inventario",
	"avance": "Avance",
	"evidencia": "Evidencia",
}

OPERATION_TYPE_LABELS = {
	"Inflow": "Ingreso",
	"Outflow": "Gasto",
	"Internal Transfer": "Transferencia interna",
	"Real Return": "Devolución real",
	"Reclassification": "Reclasificación",
	"Analytic Adjustment": "Ajuste analítico",
	"Commitment Reserve": "Reserva de compromiso",
	"Commitment Execution": "Ejecución de compromiso",
	"Commitment Release": "Liberación de compromiso",
}

STOCK_TRANSACTION_LABELS = {
	"Receipt": "Entrada de inventario",
	"Issue to Contractor": "Entrega a contratista",
	"Transfer In": "Transferencia de entrada",
	"Transfer Out": "Transferencia de salida",
	"Return": "Devolución de inventario",
	"Consumption": "Consumo",
	"Damage": "Daño",
	"Loss": "Pérdida",
}

EXCEPTION_STATUSES: dict[str, frozenset[str]] = {
	"NXR Operation": frozenset({"Cancelled", "Rejected", "Compensated Partial", "Compensated Total"}),
	"NXR Commitment": frozenset({"Cancelled", "Rejected"}),
	"NXR Purchase Request": frozenset({"Rejected", "Cancelled"}),
	"NXR Purchase Order": frozenset({"Cancelled"}),
	"NXR Goods Receipt": frozenset({"Cancelled"}),
	"NXR Contract": frozenset({"Suspended", "Cancelled Before Active", "Early Terminated"}),
	"NXR Contract Amendment": frozenset({"Cancelled Before Active"}),
	"NXR Contract Estimate": frozenset({"Rejected", "Cancelled"}),
	"NXR Stock Transaction": frozenset({"Cancelled"}),
	"NXR Progress Record": frozenset({"Rejected", "Cancelled", "Corrected"}),
	"NXR Evidence": frozenset({"Rejected", "Superseded"}),
}

MAX_LIMIT = 100
DEFAULT_LIMIT = 30
PER_SOURCE_FETCH_MULTIPLIER = 2


def resolve_actor(row: Mapping[str, Any], fields: tuple[str, ...]) -> str | None:
	for field in fields:
		value = row.get(field)
		if value:
			return str(value)
	fallback = row.get("owner")
	return str(fallback) if fallback else None


def resolve_amount(row: Mapping[str, Any], field: str | None) -> float | None:
	if not field:
		return None
	value = row.get(field)
	return float(value) if value not in (None, "") else None


def normalize_event(
	*,
	category: str,
	doctype: str,
	row: Mapping[str, Any],
	date_field: str,
	title: str,
	actor_fields: tuple[str, ...],
	amount_field: str | None,
) -> dict[str, Any] | None:
	"""Convierte una fila cruda de cualquier doctype de origen en la forma común de
	evento de la timeline. Devuelve `None` cuando la fila no tiene fecha utilizable
	— no se fabrica una fecha para que el evento aparezca de todos modos.
	"""
	date_value = row.get(date_field)
	if not date_value:
		return None
	status = str(row.get("status") or "")
	exception_statuses = EXCEPTION_STATUSES.get(doctype, frozenset())
	return {
		"key": f"{doctype}:{row.get('name')}",
		"category": category,
		"category_label": CATEGORY_LABELS[category],
		"doctype": doctype,
		"name": row.get("name"),
		"document_number": row.get("document_number") or row.get("name"),
		"date": str(date_value),
		"title": title,
		"status": status,
		"is_exception": status in exception_statuses,
		"actor": resolve_actor(row, actor_fields),
		"amount_hnl": resolve_amount(row, amount_field),
		"evidence": row.get("evidence") or None,
	}


def sort_and_truncate(events: list[dict[str, Any]], limit: int) -> tuple[list[dict[str, Any]], bool]:
	"""Orden cronológico descendente (más reciente primero) y corte al límite
	pedido. Devuelve también si quedaron eventos fuera del corte, para que el
	llamador pueda decir "hay más" en vez de sugerir que la historia terminó ahí.
	"""
	ordered = sorted(events, key=lambda event: event["date"], reverse=True)
	truncated = ordered[:limit]
	return truncated, len(ordered) > len(truncated)


def resolve_categories(requested: object, available: Mapping[str, Any]) -> list[str]:
	"""Normaliza el filtro de categorías pedido por el cliente: acepta una cadena
	suelta o una lista, ignora categorías desconocidas, y si no queda ninguna
	categoría válida devuelve todas (no un resultado vacío por un filtro mal
	escrito)."""
	if isinstance(requested, str):
		requested = [requested]
	categories = [c for c in (requested or available.keys()) if c in available]
	return categories or list(available.keys())


def clamp_limit(value: object, *, default: int = DEFAULT_LIMIT, maximum: int = MAX_LIMIT) -> int:
	# `value in (None, "")` en vez de `not value`: un límite de 0 pedido explícitamente
	# es un valor real (que luego se recorta a 1), no lo mismo que no haber mandado
	# ningún límite. `0` es falsy en Python; `if value:` los habría confundido.
	try:
		parsed = int(value) if value not in (None, "") else default
	except (TypeError, ValueError):
		parsed = default
	return min(max(parsed, 1), maximum)
