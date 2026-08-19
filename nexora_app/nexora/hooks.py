app_name = "nexora"
app_title = "NEXORA"
app_publisher = "NEXORA"
app_description = "Gestión Integral de Fondos, Proyectos y Operaciones"
app_email = "noreply@nexora.local"
app_license = "GNU General Public License v3.0"
required_apps = ["erpnext"]
# Sin esta clave el sitio caía al favicon por defecto de ERPNext/Frappe — nunca hubo
# ninguna aquí. Mismo activo que `add_to_apps_screen` para no duplicar el logo.
favicon = "/assets/nexora/images/nexora.svg"

app_include_css = [
	"/assets/nexora/css/nexora_design_system.css",
	"/assets/nexora/css/nexora_shell.css",
	"/assets/nexora/css/nexora.css",
	"/assets/nexora/css/nexora_executive.css",
	"/assets/nexora/css/nexora_command_center.css",
	"/assets/nexora/css/nexora_dashboard_fixes.css",
	"/assets/nexora/css/nexora_operational.css",
	"/assets/nexora/css/nexora_guided_operations.css",
	"/assets/nexora/css/nexora_project.css",
	"/assets/nexora/css/nexora_assistant.css",
]
app_include_js = [
	"/assets/nexora/js/nexora.js",
	"/assets/nexora/js/nexora_shell.js",
	"/assets/nexora/js/nexora_recent_routes.js",
	"/assets/nexora/js/nexora_tables.js",
	"/assets/nexora/js/nexora_quick_flows.js",
	"/assets/nexora/js/nexora_report_actions.js",
	"/assets/nexora/js/nexora_operational_ui.js",
	"/assets/nexora/js/nexora_guided_model.js",
	"/assets/nexora/js/nexora_guided_operations.js",
]

boot_session = ["nexora.boot.suppress_generic_email_password_prompt"]

override_whitelisted_methods = {
	"nexora.dashboard.executive.get_executive_snapshot": (
		"nexora.dashboard.snapshot_query.get_executive_snapshot"
	),
	"nexora.dashboard.executive.get_expense_page": ("nexora.dashboard.expense_query.get_expense_page"),
	"nexora.dashboard.service.universal_search": "nexora.permissions.secure_universal_search",
	"nexora.boot.universal_search_consolidated": "nexora.permissions.secure_universal_search_consolidated",
	"nexora.reports.service.export_report": "nexora.reports.safe_export.export_report",
	"nexora.reports.service.get_financial_report": ("nexora.reports.canonical_views.get_financial_report"),
	"nexora.reports.service.get_cost_report": "nexora.reports.canonical_views.get_cost_report",
	"nexora.reports.service.reconcile_totals": "nexora.reports.canonical_views.reconcile_totals",
	"nexora.close.service.calculate_weekly_close": "nexora.close.canonical_weekly.calculate_weekly_close",
	"nexora.close.service.save_weekly_close": "nexora.close.canonical_weekly.save_weekly_close",
	"nexora.close.service.correct_weekly_close": "nexora.close.canonical_weekly.correct_weekly_close",
	"nexora.close.service.list_weekly_closes": "nexora.close.canonical_weekly.list_weekly_closes",
	"nexora.close.service.create_monthly_close": "nexora.close.monthly_canonical.create_monthly_close",
	"nexora.close.service.transition_monthly_close": "nexora.close.monthly_canonical.transition_monthly_close",
	"nexora.close.service.correct_monthly_close": "nexora.close.monthly_canonical.correct_monthly_close",
	"nexora.close.service.list_monthly_closes": "nexora.close.monthly_canonical.list_monthly_closes",
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

doc_events = {
	"NXR Purchase Order": {
		"on_update": "nexora.purchases.financial_bridge.sync_purchase_order_financials",
	},
	"NXR Goods Receipt": {
		"on_update": "nexora.purchases.inventory_bridge.sync_goods_receipt_inventory",
	},
}

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

role_home_page = {
	"NEXORA Administrator": "app/nexora-dashboard",
	"NEXORA Finance Manager": "app/nexora-dashboard",
	"NEXORA Finance Operator": "app/nexora-dashboard",
	"NEXORA Auditor": "app/nexora-dashboard",
	"NEXORA Project Viewer": "app/nexora-dashboard",
}
