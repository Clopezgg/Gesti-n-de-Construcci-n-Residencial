from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import cint


def execute(filters=None):
	filters = frappe._dict(filters or {})
	run_name = filters.migration_run or frappe.db.get_value(
		"ConstruControl Migration Run", {}, "name", order_by="creation desc"
	)
	columns = [
		{"fieldname": "entity", "label": _("Entity"), "fieldtype": "Data", "width": 260},
		{"fieldname": "source_count", "label": _("Source"), "fieldtype": "Int", "width": 110},
		{"fieldname": "preserved_count", "label": _("Preserved"), "fieldtype": "Int", "width": 110},
		{"fieldname": "difference", "label": _("Difference"), "fieldtype": "Int", "width": 110},
		{"fieldname": "result", "label": _("Result"), "fieldtype": "Data", "width": 140},
	]
	if not run_name:
		return columns, []
	run = frappe.get_doc("ConstruControl Migration Run", run_name)
	input_counts = json.loads(run.input_counts_json or "{}")
	output_counts = json.loads(run.output_counts_json or "{}")
	ignored = {"evidence_files", "embedded_evidence_files", "storage_evidence_files", "redacted_sensitive_fields"}
	rows = []
	for entity in sorted(key for key in input_counts if key not in ignored):
		source_count = cint(input_counts.get(entity))
		preserved_count = cint(output_counts.get(f"preserved.{entity}")) if not run.dry_run else 0
		difference = preserved_count - source_count if not run.dry_run else 0
		rows.append(
			{
				"entity": entity,
				"source_count": source_count,
				"preserved_count": preserved_count,
				"difference": difference,
				"result": _("Dry Run") if run.dry_run else (_("Matched") if difference == 0 else _("Review")),
			}
		)
	return columns, rows
