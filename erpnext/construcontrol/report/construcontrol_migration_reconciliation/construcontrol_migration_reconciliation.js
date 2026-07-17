frappe.query_reports["ConstruControl Migration Reconciliation"] = {
	filters: [
		{
			fieldname: "migration_run",
			label: __("Migration Run"),
			fieldtype: "Link",
			options: "ConstruControl Migration Run",
		},
	],
};
