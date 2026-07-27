app_name = "nexora"
app_title = "NEXORA"
app_publisher = "NEXORA"
app_description = "Gestión Integral de Fondos, Proyectos y Operaciones"
app_email = "noreply@nexora.local"
app_license = "GNU General Public License v3.0"
required_apps = ["erpnext"]

app_include_css = [
	"/assets/nexora/css/nexora.css",
	"/assets/nexora/css/nexora_executive.css",
]
app_include_js = [
	"/assets/nexora/js/nexora.js",
	"/assets/nexora/js/nexora_quick_flows.js",
	"/assets/nexora/js/nexora_report_actions.js",
]

override_whitelisted_methods = {
	"nexora.dashboard.executive.get_executive_snapshot": (
		"nexora.dashboard.snapshot_query.get_executive_snapshot"
	),
	"nexora.dashboard.executive.get_expense_page": "nexora.dashboard.expense_query.get_expense_page",
	"nexora.reports.service.export_report": "nexora.reports.safe_export.export_report",
	"nexora.reports.service.get_financial_report": ("nexora.reports.canonical_views.get_financial_report"),
	"nexora.reports.service.get_cost_report": "nexora.reports.canonical_views.get_cost_report",
	"nexora.reports.service.reconcile_totals": "nexora.reports.canonical_views.reconcile_totals",
	"nexora.close.service.calculate_weekly_close": ("nexora.close.canonical_weekly.calculate_weekly_close"),
	"nexora.close.service.save_weekly_close": "nexora.close.canonical_weekly.save_weekly_close",
	"nexora.close.service.correct_weekly_close": "nexora.close.canonical_weekly.correct_weekly_close",
	"nexora.close.service.list_weekly_closes": "nexora.close.canonical_weekly.list_weekly_closes",
}

fixtures = [
	{
		"dt": "Role",
		"filters": [
			[
				"name",
				"in",
				[
					"NEXORA Administrator",
					"NEXORA Finance Manager",
					"NEXORA Finance Operator",
					"NEXORA Auditor",
					"NEXORA Project Viewer",
				],
			]
		],
	}
]

before_request = ["nexora.directory.api.bootstrap", "nexora.contracts.api.bootstrap"]
after_install = "nexora.install.after_install"
after_migrate = "nexora.install.after_migrate"
before_uninstall = "nexora.install.before_uninstall"
after_uninstall = "nexora.install.after_uninstall"

add_to_apps_screen = [
	{
		"name": "nexora",
		"logo": "/assets/nexora/images/nexora.svg",
		"title": "NEXORA",
		"route": "/app/nexora-dashboard",
		"has_permission": "nexora.permissions.can_access_nexora",
	}
]
