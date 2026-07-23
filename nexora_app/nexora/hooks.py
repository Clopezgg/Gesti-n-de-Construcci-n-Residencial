app_name = "nexora"
app_title = "NEXORA"
app_publisher = "NEXORA"
app_description = "Gestión Integral de Fondos, Proyectos y Operaciones"
app_email = "noreply@nexora.local"
app_license = "GNU General Public License v3.0"
required_apps = ["erpnext"]

app_include_css = "/assets/nexora/css/nexora.css"
app_include_js = "/assets/nexora/js/nexora.js"

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

after_install = "nexora.install.after_install"
after_migrate = "nexora.install.after_migrate"
before_uninstall = "nexora.install.before_uninstall"
after_uninstall = "nexora.install.after_uninstall"

add_to_apps_screen = [
	{
		"name": "nexora",
		"logo": "/assets/nexora/images/nexora.svg",
		"title": "NEXORA",
		"route": "/app/nexora",
		"has_permission": "nexora.permissions.can_access_nexora",
	}
]
