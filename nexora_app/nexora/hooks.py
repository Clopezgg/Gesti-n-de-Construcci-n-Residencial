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
# NO declarar `app_logo_url` aquí: `frappe.core.doctype.navbar_settings.
# navbar_settings.get_app_logo()` (fuente real verificada, Frappe v15) solo usa
# la lista de hooks `app_logo_url` de TODAS las apps instaladas cuando
# `Website Settings.app_logo`/`Navbar Settings.app_logo` están vacíos, y
# entonces solo toma `logos[1]` si la lista tiene EXACTAMENTE dos elementos —
# con `frappe` + `erpnext` + `nexora` la lista tiene tres, así que cae a
# `logos[0]` (el logo del propio Frappe), peor que no declarar nada. Confirmado
# con una captura real de CI que empeoró justo así (Bloque 160, primer
# intento). El mark real de NEXORA se fija de forma confiable en
# `install.py::_ensure_navbar_logo()` contra `Website Settings.app_logo`, que
# `get_app_logo()` consulta primero, sin depender de cuántas apps declaren el
# hook.

app_include_css = [
	"/assets/nexora/css/nexora_design_system.css",
	"/assets/nexora/css/nexora_shell.css",
	"/assets/nexora/css/nexora_native_desk.css",
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
# `nexora.shell_guard.enforce` vive aquí, no en `before_request`: solo dentro del
# renderizado de una página `www` (que incluye `/app`, el Desk) `frappe.Redirect`
# produce una redirección HTTP real — ver el docstring de `nexora/shell_guard.py`.
update_website_context = ["nexora.shell_guard.enforce"]
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
	# CORRECCIÓN ESTRUCTURAL DEL DESK FRAPPE: "System Manager" nunca tuvo
	# entrada aquí — el usuario real "Administrator" (superusuario incorporado
	# de Frappe) siempre tiene este rol, casi nunca "NEXORA Administrator"
	# asignado explícitamente. Sin esta entrada, la resolución de página de
	# inicio por rol nunca encontraba una coincidencia para ese usuario y
	# caía al Workspace "Home" genérico de ERPNext ("Let's begin your
	# journey with ERPNext") — la causa raíz real confirmada de ese hallazgo,
	# no una suposición.
	"System Manager": "app/nexora-dashboard",
	"NEXORA Administrator": "app/nexora-dashboard",
	"NEXORA Finance Manager": "app/nexora-dashboard",
	"NEXORA Finance Operator": "app/nexora-dashboard",
	"NEXORA Auditor": "app/nexora-dashboard",
	"NEXORA Project Viewer": "app/nexora-dashboard",
}
