from __future__ import annotations


def ensure_weekly_fields() -> None:
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(
		{
			"CC Weekly Closing": [
				{
					"fieldname": "pending_expense_hnl",
					"label": "Gastos pendientes",
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
					"insert_after": "pending_expense_hnl",
				},
				{
					"fieldname": "progress_update_count",
					"label": "Avances registrados",
					"fieldtype": "Int",
					"read_only": 1,
					"insert_after": "inventory_movement_count",
				},
				{
					"fieldname": "pending_items_json",
					"label": "Pendientes",
					"fieldtype": "Code",
					"options": "JSON",
					"read_only": 1,
					"insert_after": "progress_update_count",
				},
				{
					"fieldname": "generated_at",
					"label": "Generado",
					"fieldtype": "Datetime",
					"read_only": 1,
					"insert_after": "pending_items_json",
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
			]
		},
		update=True,
	)


__all__ = ["ensure_weekly_fields"]
