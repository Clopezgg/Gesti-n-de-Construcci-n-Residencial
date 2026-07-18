"""ConstruControl operational migration entry point.

Kept at the original import path so existing integrations continue working while
the implementation lives in the audited operational importer.
"""

from collections.abc import Mapping
from typing import Any

from erpnext.construcontrol.migration import operational_importer as _operational

ENTITY_DOCTYPES = _operational.ENTITY_DOCTYPES
validate_payload = _operational.validate_payload
_original_values = _operational._values


def _normalized_values(
    entity: str,
    record: Mapping[str, Any],
    source_id: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Normalize legacy values before Frappe validates Select fields."""
    values = _original_values(entity, record, source_id, context)
    if entity == "settings":
        values["address"] = record.get("projectAddress") or record.get("address")
        values["original_budget_hnl"] = record.get("originalBudgetHnl") or record.get("totalBudgetHnl") or 0
    elif entity == "expenses":
        if values.get("financial_status") not in {"pending", "paid", "cancelled", "reimbursed"}:
            values["financial_status"] = "pending" if record.get("status") == "pending" else "paid"
        if not record.get("commercialSource") and not record.get("source"):
            values["commercial_source"] = {
                "labor": "MANO DE OBRA",
                "materials": "FERRETERÍA / MATERIALES",
                "transport": "FLETE O TRANSPORTE",
                "machinery": "MAQUINARIA",
                "service": "SERVICIO",
                "permit": "PERMISO",
            }.get(str(record.get("category")), str(record.get("category") or "OTRO").upper())
    return values


_operational._values = _normalized_values
run_import = _operational.run_import

__all__ = ["ENTITY_DOCTYPES", "run_import", "validate_payload"]
