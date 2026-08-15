app_name = "nexora"
app_title = "NEXORA"
app_publisher = "NEXORA"
app_description = "Gestión Integral de Fondos, Proyectos y Operaciones"
app_email = "noreply@nexora.local"
app_license = "GNU General Public License v3.0"
required_apps = ["erpnext"]

app_include_css = [
	# El sistema de diseño va primero y sin excepción: define las variables que consumen
	# todas las hojas siguientes. Cargarlo después las dejaría resolviendo tokens que
	# todavía no existen.
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
	"nexora.dashboard.executive.get_expense_page": "nexora.dashboard.expense_query.get_expense_page",
	"nexora.dashboard.service.universal_search": "nexora.permissions.secure_universal_search",
	"nexora.boot.universal_search_consolidated": "nexora.permissions.secure_universal_search_consolidated",
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

doc_events = {
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

# `desktop:home_page` (nexora.install) solo gobierna `/app`. El sitio web —fuera de
# `/app`— resuelve su propio destino por separado (`frappe.website.utils.get_home_page`):
# primero mira `Role.home_page`, y si ningún rol del usuario lo trae, cae hasta "me", la
# página de cuenta de Frappe — que a su vez expone el menú de portal por defecto de
# ERPNext (Proyectos, Solicitudes de presupuesto, Órdenes, Facturas, Envíos,
# Incidencias). Ninguno de los roles NEXORA traía `home_page`, así que cualquier usuario
# NEXORA que llegara a la raíz del sitio (fuera de `/app`) caía directo en ese portal
# genérico de ERPNext — la fuga real detrás de las capturas "Mi Cuenta"/"Órdenes"/
# "Facturas". `role_home_page` es el punto de extensión que Frappe ya lee en ese mismo
# fallback antes de llegar a "me".
role_home_page = {
	"NEXORA Administrator": "app/nexora-dashboard",
	"NEXORA Finance Manager": "app/nexora-dashboard",
	"NEXORA Finance Operator": "app/nexora-dashboard",
	"NEXORA Auditor": "app/nexora-dashboard",
	"NEXORA Project Viewer": "app/nexora-dashboard",
}
