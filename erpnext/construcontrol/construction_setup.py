from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def ensure_construction_fields() -> None:
	create_custom_fields(
		{
			"CC Project Profile": [
				{
					"fieldname": "executive_control_section",
					"label": "Control ejecutivo de la obra",
					"fieldtype": "Section Break",
					"insert_after": "original_budget_hnl",
				},
				{
					"fieldname": "updated_budget_hnl",
					"label": "Presupuesto actualizado (L)",
					"fieldtype": "Currency",
					"options": "HNL",
					"insert_after": "executive_control_section",
				},
				{
					"fieldname": "committed_hnl",
					"label": "Comprometido (L)",
					"fieldtype": "Currency",
					"options": "HNL",
					"read_only": 1,
					"insert_after": "updated_budget_hnl",
				},
				{
					"fieldname": "actual_cost_hnl",
					"label": "Costo real (L)",
					"fieldtype": "Currency",
					"options": "HNL",
					"read_only": 1,
					"insert_after": "committed_hnl",
				},
				{
					"fieldname": "available_budget_hnl",
					"label": "Presupuesto disponible (L)",
					"fieldtype": "Currency",
					"options": "HNL",
					"read_only": 1,
					"insert_after": "actual_cost_hnl",
				},
				{
					"fieldname": "physical_progress_percent",
					"label": "Avance físico (%)",
					"fieldtype": "Percent",
					"read_only": 1,
					"insert_after": "available_budget_hnl",
				},
				{
					"fieldname": "financial_progress_percent",
					"label": "Avance financiero (%)",
					"fieldtype": "Percent",
					"read_only": 1,
					"insert_after": "physical_progress_percent",
				},
				{
					"fieldname": "budget_variance_hnl",
					"label": "Desviación presupuestaria (L)",
					"fieldtype": "Currency",
					"options": "HNL",
					"read_only": 1,
					"insert_after": "financial_progress_percent",
				},
				{
					"fieldname": "schedule_status",
					"label": "Estado del cronograma",
					"fieldtype": "Select",
					"options": "on_track\nat_risk\ndelayed\ncompleted",
					"default": "on_track",
					"in_list_view": 1,
					"insert_after": "budget_variance_hnl",
				},
				{
					"fieldname": "alert_level",
					"label": "Nivel de alerta",
					"fieldtype": "Select",
					"options": "normal\nattention\ncritical",
					"default": "normal",
					"in_list_view": 1,
					"insert_after": "schedule_status",
				},
				{
					"fieldname": "next_milestone",
					"label": "Próximo hito",
					"fieldtype": "Data",
					"insert_after": "alert_level",
				},
				{
					"fieldname": "next_milestone_date",
					"label": "Fecha del próximo hito",
					"fieldtype": "Date",
					"insert_after": "next_milestone",
				},
			],
			"CC Construction Phase": [
				{
					"fieldname": "phase_control_section",
					"label": "Control de fase",
					"fieldtype": "Section Break",
					"insert_after": "progress_percent",
				},
				{
					"fieldname": "committed_hnl",
					"label": "Comprometido (L)",
					"fieldtype": "Currency",
					"options": "HNL",
					"read_only": 1,
					"insert_after": "phase_control_section",
				},
				{
					"fieldname": "actual_cost_hnl",
					"label": "Costo real (L)",
					"fieldtype": "Currency",
					"options": "HNL",
					"read_only": 1,
					"insert_after": "committed_hnl",
				},
				{
					"fieldname": "available_budget_hnl",
					"label": "Disponible (L)",
					"fieldtype": "Currency",
					"options": "HNL",
					"read_only": 1,
					"insert_after": "actual_cost_hnl",
				},
				{
					"fieldname": "financial_progress_percent",
					"label": "Avance financiero (%)",
					"fieldtype": "Percent",
					"read_only": 1,
					"insert_after": "available_budget_hnl",
				},
				{
					"fieldname": "schedule_status",
					"label": "Estado del cronograma",
					"fieldtype": "Select",
					"options": "not_started\non_track\nat_risk\ndelayed\ncompleted",
					"default": "not_started",
					"in_list_view": 1,
					"insert_after": "financial_progress_percent",
				},
				{
					"fieldname": "milestone_date",
					"label": "Fecha de hito",
					"fieldtype": "Date",
					"insert_after": "schedule_status",
				},
				{
					"fieldname": "dependencies",
					"label": "Dependencias",
					"fieldtype": "Small Text",
					"insert_after": "milestone_date",
				},
				{
					"fieldname": "responsible_user",
					"label": "Responsable del sistema",
					"fieldtype": "Link",
					"options": "User",
					"insert_after": "dependencies",
				},
			],
		},
		update=True,
	)
	frappe.clear_cache(doctype="CC Project Profile")
	frappe.clear_cache(doctype="CC Construction Phase")


__all__ = ["ensure_construction_fields"]
