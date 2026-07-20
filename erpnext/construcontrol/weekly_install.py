from __future__ import annotations

from typing import Any


def _exclude_standard_fields(
	definitions: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
	import frappe

	filtered: dict[str, list[dict[str, Any]]] = {}
	for doctype, fields in definitions.items():
		standard = set(frappe.get_all("DocField", filters={"parent": doctype}, pluck="fieldname"))
		filtered[doctype] = [field for field in fields if field.get("fieldname") not in standard]
	return filtered


def ensure_weekly_fields() -> None:
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	definitions: dict[str, list[dict[str, Any]]] = {
		"CC Weekly Closing": [
			{
				"fieldname": "recognized_expense_hnl",
				"label": "Gasto reconocido",
				"fieldtype": "Currency",
				"options": "HNL",
				"read_only": 1,
				"insert_after": "expense_hnl",
			},
			{
				"fieldname": "pending_expense_hnl",
				"label": "Gastos pendientes",
				"fieldtype": "Currency",
				"options": "HNL",
				"read_only": 1,
				"insert_after": "recognized_expense_hnl",
			},
			{
				"fieldname": "committed_hnl",
				"label": "Comprometido",
				"fieldtype": "Currency",
				"options": "HNL",
				"read_only": 1,
				"insert_after": "pending_expense_hnl",
			},
			{
				"fieldname": "projected_balance_hnl",
				"label": "Saldo proyectado",
				"fieldtype": "Currency",
				"options": "HNL",
				"read_only": 1,
				"insert_after": "final_balance_hnl",
			},
			{
				"fieldname": "inventory_movement_count",
				"label": "Movimientos de inventario",
				"fieldtype": "Int",
				"read_only": 1,
				"insert_after": "projected_balance_hnl",
			},
			{
				"fieldname": "progress_update_count",
				"label": "Avances registrados",
				"fieldtype": "Int",
				"read_only": 1,
				"insert_after": "inventory_movement_count",
			},
			{
				"fieldname": "quality_failure_count",
				"label": "Incidencias de calidad",
				"fieldtype": "Int",
				"read_only": 1,
				"insert_after": "progress_update_count",
			},
			{
				"fieldname": "reconciliation_status",
				"label": "Conciliación",
				"fieldtype": "Select",
				"options": "pending\nreconciled",
				"read_only": 1,
				"insert_after": "quality_failure_count",
			},
			{
				"fieldname": "pending_items_json",
				"label": "Pendientes",
				"fieldtype": "Code",
				"options": "JSON",
				"read_only": 1,
				"insert_after": "reconciliation_status",
			},
			{
				"fieldname": "snapshot_digest",
				"label": "Huella SHA-256",
				"fieldtype": "Data",
				"read_only": 1,
				"insert_after": "pending_items_json",
			},
			{
				"fieldname": "generated_at",
				"label": "Generado",
				"fieldtype": "Datetime",
				"read_only": 1,
				"insert_after": "snapshot_digest",
			},
			{
				"fieldname": "generated_by_name",
				"label": "Generado por",
				"fieldtype": "Data",
				"read_only": 1,
				"insert_after": "generated_at",
				"in_list_view": 1,
			},
			{
				"fieldname": "generated_by_email",
				"label": "Correo",
				"fieldtype": "Data",
				"read_only": 1,
				"insert_after": "generated_by_name",
			},
			{
				"fieldname": "generated_by_role",
				"label": "Rol",
				"fieldtype": "Data",
				"read_only": 1,
				"insert_after": "generated_by_email",
				"in_list_view": 1,
			},
			{
				"fieldname": "reopened_by",
				"label": "Reabierto por",
				"fieldtype": "Link",
				"options": "User",
				"read_only": 1,
				"insert_after": "generated_by_role",
			},
			{
				"fieldname": "reopened_at",
				"label": "Fecha de reapertura",
				"fieldtype": "Datetime",
				"read_only": 1,
				"insert_after": "reopened_by",
			},
			{
				"fieldname": "reopen_reason",
				"label": "Motivo de reapertura",
				"fieldtype": "Small Text",
				"read_only": 1,
				"insert_after": "reopened_at",
			},
		],
	}
	create_custom_fields(_exclude_standard_fields(definitions), update=True)
