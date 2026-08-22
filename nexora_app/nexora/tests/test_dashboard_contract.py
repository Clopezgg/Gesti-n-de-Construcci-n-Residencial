from __future__ import annotations

import json
import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestDashboardContract(unittest.TestCase):
	@staticmethod
	def _dashboard_code() -> str:
		return (APP_ROOT / "nexora/page/nexora_dashboard/nexora_dashboard.js").read_text(encoding="utf-8")

	def test_dashboard_module_and_service_exist(self) -> None:
		self.assertTrue((APP_ROOT / "dashboard/__init__.py").is_file())
		self.assertTrue((APP_ROOT / "dashboard/service.py").is_file())

	def test_dashboard_and_search_pages_exist(self) -> None:
		for page_name in ("nexora-dashboard", "nexora-search"):
			# Frappe resolves page assets with frappe.scrub(name), so the folder and the
			# asset filenames use underscores even when the Page record uses hyphens.
			folder = page_name.replace("-", "_")
			root = APP_ROOT / f"nexora/page/{folder}"
			payload = json.loads((root / f"{folder}.json").read_text(encoding="utf-8"))
			self.assertEqual(page_name, payload["page_name"])
			self.assertIn("frappe.pages", (root / f"{folder}.js").read_text(encoding="utf-8"))

	def test_dashboard_keeps_project_control_reference(self) -> None:
		code = self._dashboard_code()
		self.assertIn("const projectControl = page.add_field", code)
		self.assertIn("projectControl.get_value()", code)
		self.assertNotIn("controls.project.get_value()", code)

	def test_dashboard_exposes_direct_income_and_expense_actions(self) -> None:
		code = self._dashboard_code()
		for marker in (
			'data-action="income"',
			'data-action="expense"',
			"frappe.route_options",
			"nexora_action: action",
			"project: projectControl.get_value()",
		):
			self.assertIn(marker, code)

	def test_dashboard_uses_official_product_identity(self) -> None:
		code = self._dashboard_code()
		self.assertIn('title: __("NEXORA")', code)
		self.assertIn("Gestión Integral de Fondos, Proyectos y Operaciones", code)
		self.assertNotIn("NEXORA — Control de obras", code)

	def test_dashboard_translates_technical_operation_values(self) -> None:
		code = self._dashboard_code()
		for marker in (
			'Inflow: __("Fondo")',
			'Outflow: __("Gasto")',
			'"Internal Transfer": __("Transferencia interna")',
			'"Real Return": __("Devolución real")',
			'Draft: __("Borrador")',
			'Executed: __("Registrado definitivamente")',
			'Posted: __("Registrado definitivamente")',
			'"Compensated Total": __("Corregido totalmente")',
		):
			self.assertIn(marker, code)

	def test_dashboard_handles_loading_failures_with_actionable_copy(self) -> None:
		code = self._dashboard_code()
		for marker in (
			"try {",
			"catch (error)",
			'title: __("Resumen no disponible")',
			"Revise la conexión, el proyecto o sus permisos y vuelva a intentar.",
			'attr({ "data-state": "error", "aria-busy": "false" })',
		):
			self.assertIn(marker, code)

	def test_error_fallback_never_shows_two_dialogs(self) -> None:
		"""`showError` no devuelve valor. Encadenarlo con `||` ejecutaba el respaldo
		siempre y el usuario veía el mismo error dos veces, uno encima del otro. El
		respaldo existe solo para cuando el bundle compartido no cargó, así que la
		rama tiene que ser explícita."""
		shared = (APP_ROOT / "public/js/nexora_report_actions.js").read_text(encoding="utf-8")
		body = shared.split("function showError(", 1)[1].split("\n\t}", 1)[0]
		self.assertNotIn("return", body, "si showError devolviera algo, el contrato cambiaría")

		for relative in (
			"nexora/page/nexora_dashboard/nexora_dashboard.js",
			"nexora/page/nexora_operations/nexora_operations.js",
		):
			with self.subTest(surface=relative):
				code = (APP_ROOT / relative).read_text(encoding="utf-8")
				self.assertNotRegex(
					code,
					r"showError\??\.?\([^;]*\}\)\s*\|\|",
					"encadenar el respaldo con || duplica el diálogo",
				)
				self.assertIn("typeof window.nexora", code)
				self.assertIn("frappe.msgprint(", code)

	def test_dashboard_snapshot_uses_native_deadline_instead_of_frappe_thenable(self) -> None:
		code = self._dashboard_code()
		snapshot_request = code[
			code.index("function requestExecutiveSnapshot") : code.index("function renderIdentity")
		]
		load = code[code.index("async function load") : code.index("function render(data)")]
		for marker in (
			"return new Promise((resolve, reject) => {",
			"window.setTimeout(",
			"120000",
			"callback: (response) => finish(resolve, response?.message || {})",
			"error: (error) =>",
			"El resumen ejecutivo excedió 120 segundos.",
		):
			self.assertIn(marker, snapshot_request)
		self.assertIn(
			"const snapshot = await requestExecutiveSnapshot(snapshotPayload(), Boolean(freeze));",
			load,
		)
		self.assertNotIn("await frappe.call", load)
		self.assertIn("render(snapshot)", load)

	def test_dashboard_period_label_keeps_its_colon(self) -> None:
		"""Regresión real (Bloque 30): el PR #93 (`c513789d`, "make dashboard period
		selectable") sustituyó el texto plano `Período: <mes>` por un `<select>` y en
		el cambio perdió los dos puntos — `.nxr-dashboard-period` quedó como
		`Período<select>...` en vez de `Período: <select>...`. El recorrido real de
		Playwright (`nexora_browser_validators.mjs::validateDashboard`) exige que el
		texto visible empiece con `/^Período:/`; sin los dos puntos, la etapa `panel`
		fallaba en los tres perfiles en cada ejecución real desde ese PR — la causa
		raíz del defecto que los Bloques 24 a 29 documentaron como "preexistente y
		ajeno" sin diagnosticarlo."""
		code = self._dashboard_code()
		render_identity = code[code.index("function renderIdentity") : code.index("function periodKey")]
		self.assertIn('${__("Período")}: ${periodSelect(activePeriod)}', render_identity)

	def test_dashboard_integrates_complete_operational_summary(self) -> None:
		"""AUDITORÍA VISUAL Y FUNCIONAL COMPLETA POST-DASHBOARD: `finance.total_available_hnl`/
		`finance.total_reserved_hnl`/`executive.spent_hnl` solo aparecían en la fila de
		seis métricas ya retirada (`renderMetrics`) — la misma información real sigue
		en el panel a través de `executive.cash_available_hnl`/`executive.committed_hnl`
		(fila real de KPI) y `budgets.total_executed_hnl` (donut de ejecución
		presupuestaria), nunca perdida."""
		code = self._dashboard_code()
		for marker in (
			"executive.cash_available_hnl",
			"executive.committed_hnl",
			"budgets.total_executed_hnl",
			"budgets.total_available_hnl",
			"pending_accounts",
			"progress.physical_percent",
			"nxr-evidence-gallery",
			"nxr-alert-rows",
			"nxr-contract-rows",
		):
			self.assertIn(marker, code)

	def test_dashboard_service_reconciles_against_canonical_effect_ledger(self) -> None:
		code = (APP_ROOT / "dashboard/service.py").read_text(encoding="utf-8")
		for marker in (
			"source_states",
			'"NXR Operation Effect"',
			'"Reserved"',
			'"Budget"',
			'{"Commitment Reserve", "Commitment Release"}',
			'"NXR Contract Estimate"',
			'"NXR Progress Record"',
			'"NXR Evidence"',
		):
			self.assertIn(marker, code)

	def test_service_has_whitelisted_permission_checked_functions(self) -> None:
		code = (APP_ROOT / "dashboard/service.py").read_text(encoding="utf-8")
		for marker in (
			"@frappe.whitelist",
			"def universal_search",
			"def get_dashboard_summary",
			"require_action",
		):
			self.assertIn(marker, code)

	def test_workspace_has_dashboard_and_search_shortcuts(self) -> None:
		payload = json.loads((APP_ROOT / "nexora/workspace/nexora/nexora.json").read_text(encoding="utf-8"))
		shortcuts = [shortcut["label"] for shortcut in payload.get("shortcuts", [])]
		self.assertIn("Panel principal", shortcuts)
		self.assertIn("Buscador universal", shortcuts)

	def test_global_navigation_uses_canonical_nexora_pages(self) -> None:
		"""La navegación se mudó de `nexora.js` —donde era una tira de enlaces inyectada en
		el cuerpo de la página— a la carcasa, que la agrupa por la pregunta que responde
		cada grupo en vez de listar doce destinos iguales en fila."""
		shell = (APP_ROOT / "public/js/nexora_shell.js").read_text(encoding="utf-8")
		for route in (
			"nexora-dashboard",
			"nexora-assistant",
			"nexora-operations",
			"nexora-search",
			"nexora-finance",
			"nexora-reports",
			"nexora-closing",
			"nexora-purchase-requests",
			"nexora-quotations",
			"nexora-suppliers",
			"nexora-contracts",
			"nexora-entities",
			"nexora-evidence",
			"nexora-progress",
			"nexora-conversation-channels",
			"nexora-ai-providers",
			"nexora-administracion",
			"nexora-purchase-orders",
			"nexora-inventory",
			"nexora-budget",
			"nexora-quality",
			"nexora-receipts",
			"nexora-integrations",
			"nexora-notifications",
		):
			with self.subTest(route=route):
				self.assertIn(f'route: "{route}"', shell)
		# Los doce originales siguen estando en `SECTIONS`, el cajón lateral: la
		# reorganización no puede perder destinos por el camino. Se cuenta solo dentro
		# de ese arreglo, no en todo el archivo — NXR-UX-0014 agregó `TABBAR_ITEMS`, una
		# barra inferior de teléfono que referencia cuatro de estos mismos destinos (no
		# crea rutas nuevas), y contar el archivo completo los sumaría como distintos.
		# NXR-UX-0010 (Bloque 17) sumó un decimotercer destino real y nuevo
		# ("nexora-project"); NXR-CNV-0001 (Bloque 18) sumó un decimocuarto
		# ("nexora-assistant"); Bloque 25 (NXR-AVA-0006) sumó un decimoquinto
		# ("nexora-progress" — la página de avance que la matriz de requisitos daba
		# por implementada sin que existiera); un hallazgo de auditoría anterior sumó
		# un decimosexto y un decimoséptimo ("nexora-conversation-channels" y
		# "nexora-ai-providers" — páginas reales que habían quedado huérfanas de esta
		# misma navegación desde que reemplazó al workspace legado). Sesión
		# 2026-08-16 (Bloques 48/50/51), mismo hallazgo repetido tres veces más:
		# "nexora-administracion" (decimoctavo — no existía ninguna zona propia de
		# NEXORA para usuarios/roles), "nexora-purchase-orders" (decimonoveno — la
		# única forma de crear/mover una orden era el escritorio técnico de Frappe)
		# y "nexora-inventory" (vigésimo — sin ninguna interfaz para registrar un
		# movimiento). Bloque 53 sumó un vigesimoprimero, "nexora-budget" — mismo
		# hallazgo: `budget.service` no tenía ni lectura ni ninguna página propia.
		# Bloque 54 sumó un vigesimosegundo, "nexora-quality" — `quality.service`
		# existe desde el Bloque 13 sin ningún punto de entrada real. Bloque 57
		# sumó un vigesimotercero, "nexora-receipts" — mismo hallazgo original del
		# Bloque 50 (GP-04, paso "recepción"), resuelto en un bloque aparte. Un
		# bloque posterior al 58 sumó un vigesimocuarto, "nexora-integrations" —
		# siete funciones reales de `integrations.service`/`integrations.sap`
		# sin ningún llamador en todo el repositorio. Un bloque posterior al 59
		# sumó un vigesimoquinto, "nexora-notifications" — cuatro funciones
		# reales de `notifications.service` sin ningún llamador: ni el propio
		# destinatario podía ver o marcar como leída una notificación suya sin
		# llamar la API a mano. El bloque de cierre de producción (Paso 2) sumó
		# un vigesimosexto, "nexora-sap" — SAP dejó de vivir escondido dentro
		# de la tabla genérica de "nexora-integrations" y ganó su propia
		# superficie, con su propia entrada de navegación. RECONSTRUCCIÓN
		# VISUAL DEFINITIVA reagrupó los seis grupos con los nombres exactos
		# del mandato del propietario sin quitar ningún destino real — y sumó
		# tres entradas más que apuntan a la misma página real
		# "nexora-reports" con una vista distinta ("Estados de cuenta" con
		# `report: "FI01"`, "Indicadores" con `report: "PR03"` y
		# "Exportaciones"), en vez de inventar una ruta nueva que no existe.
		# 29 es el conteo correcto ahora (26 + 3).
		sections_block = shell.split("const SECTIONS = [", 1)[1].split("\n\t];", 1)[0]
		self.assertEqual(29, sections_block.count('{ route: "'), "faltan o sobran destinos")
		self.assertIn('route: "nexora-project"', sections_block)
		self.assertIn('route: "nexora-assistant"', sections_block)
		self.assertIn('route: "nexora-progress"', sections_block)
		self.assertIn('route: "nexora-conversation-channels"', sections_block)
		self.assertIn('route: "nexora-ai-providers"', sections_block)
		self.assertIn('route: "nexora-administracion"', sections_block)
		self.assertIn('route: "nexora-purchase-orders"', sections_block)
		self.assertIn('route: "nexora-inventory"', sections_block)
		self.assertIn('route: "nexora-budget"', sections_block)
		self.assertIn('route: "nexora-quality"', sections_block)
		self.assertIn('route: "nexora-receipts"', sections_block)
		self.assertIn('route: "nexora-integrations"', sections_block)
		self.assertIn('route: "nexora-notifications"', sections_block)
		self.assertIn('route: "nexora-sap"', sections_block)
		# Bloque 51 (2026-08-16) agregó un sexto grupo, "Inventario" — el modelo de
		# navegación no tenía ninguna sección propia para movimientos de inventario.
		self.assertEqual(6, shell.count("\t\t\tlabel: "), "seis grupos, no doce iguales")
		self.assertIn('frappe.boot?.home_page === "nexora-dashboard"', shell)

	def test_the_dashboard_answers_what_to_do_today(self) -> None:
		"""AUDITORÍA VISUAL Y FUNCIONAL COMPLETA POST-DASHBOARD: el propio "Qué requiere
		su atención hoy" (`renderAgenda`) se había vuelto el defecto que originalmente
		vino a corregir — una segunda sección respondiendo la misma pregunta que el
		panel "Notificaciones" del bloque central (`renderCentralNotifications`) ya
		resuelve desde la reconstrucción visual definitiva (pagos vencidos/próximos,
		cumplimiento por vencer). Se retiró `renderAgenda`/`.nxr-agenda` por completo —
		nunca se dejan dos secciones activas para la misma pregunta— y sus dos señales
		que el panel de notificaciones todavía no cubría (fondos sin conciliar, alertas
		genéricas del snapshot) se trasladaron ahí en vez de perderse."""
		code = self._dashboard_code()
		self.assertNotIn("function renderAgenda(", code)
		self.assertNotIn('class="nxr-agenda"', code)
		notifications = code.split("function renderCentralNotifications(data) {", 1)[1].split("\n\t}", 1)[0]
		for source in (
			"data.pending_accounts",
			"data.compliance_alerts",
			"analytics?.unreconciled_count",
			"data.alerts",
		):
			with self.subTest(source=source):
				self.assertIn(source, notifications)
		self.assertIn("Fondos sin conciliar", notifications)
		# No pide nada nuevo al servidor: si lo hiciera, el panel tardaría más en abrirse.
		self.assertNotIn("frappe.call", notifications)

	def test_dashboard_is_the_canonical_desk_home(self) -> None:
		hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
		install = (APP_ROOT / "install.py").read_text(encoding="utf-8")
		self.assertIn('"route": "/app/nexora-dashboard"', hooks)
		self.assertIn('NEXORA_HOME_PAGE = "nexora-dashboard"', install)
		self.assertIn('frappe.db.set_default("desktop:home_page", NEXORA_HOME_PAGE)', install)

	def test_dashboard_styles_cover_mobile_composition(self) -> None:
		css = (APP_ROOT / "public/css/nexora.css").read_text(encoding="utf-8")
		for selector in (
			".nxr-dashboard-shell",
			".nxr-dashboard-welcome",
			".nxr-section-heading",
			".nxr-dashboard-primary-actions",
			".nxr-balance-row",
			".nxr-evidence-gallery",
			".nxr-progress-track",
			".nxr-list-row",
		):
			self.assertIn(selector, css)

	def test_dashboard_context_is_consumed_by_related_pages(self) -> None:
		for relative_path in (
			"nexora/page/nexora_evidence/nexora_evidence.js",
			"nexora/page/nexora_reports/nexora_reports.js",
			"nexora/page/nexora_contracts/nexora_contracts.js",
			"nexora/page/nexora_purchase_requests/nexora_purchase_requests.js",
		):
			code = (APP_ROOT / relative_path).read_text(encoding="utf-8")
			self.assertIn("frappe.route_options", code)
			self.assertIn("launchOptions.project", code)

	def test_financial_report_sends_resolved_payload(self) -> None:
		code = (APP_ROOT / "nexora/page/nexora_reports/nexora_reports.js").read_text(encoding="utf-8")
		self.assertIn("args: { payload: payload() }", code)
		self.assertNotIn("args: { payload },", code)

	def test_search_result_detail_translates_dimension_and_effect_type(self) -> None:
		"""Hallazgo real de auditoría visual (captura real del recorrido de
		navegador, `desktop-chromium-universal-search.png`): la tabla «Efecto
		financiero» del consolidado de búsqueda pintaba `effect.dimension`/
		`effect.effect_type` sin traducir — el valor interno en inglés que
		`financial/db.py` escribe en `NXR Operation Effect` ("Funds", "Cost
		Recognized", "Budget Executed"…) aparecía tal cual junto a etiquetas en
		español en la misma fila. Único punto de la interfaz que muestra estos
		dos campos: se corrige aquí con el mismo registro de traducciones que ya
		usa el resto de la aplicación (`window.nexora.ui.label`), no con un
		diccionario nuevo y local."""
		search = (APP_ROOT / "nexora/page/nexora_search/nexora_search.js").read_text(encoding="utf-8")
		self.assertIn('ui.label("dimension", effect.dimension)', search)
		self.assertIn('ui.label("effectType", effect.effect_type)', search)
		self.assertNotIn("escape(effect.dimension)", search)
		self.assertNotIn("escape(effect.effect_type)", search)

		registry = (APP_ROOT / "public/js/nexora_report_actions.js").read_text(encoding="utf-8")
		dimension_block = registry.split("dimension: Object.freeze({", 1)[1].split("}),", 1)[0]
		effect_type_block = registry.split("effectType: Object.freeze({", 1)[1].split("}),", 1)[0]
		# Conjunto real, tomado de los literales de financial/db.py,
		# operational_commands.py y corrections.py — no inventado.
		for value in ("Funds", "Reserved", "Cost", "Budget", "Savings", "Investment"):
			with self.subTest(dimension=value):
				self.assertIn(f"{value}:", dimension_block)
		for value in (
			"Executed",
			"Reserved",
			"Released",
			"Internal Transfer",
			"Real Return",
			"Analytic Adjustment",
			"Reclassification",
			"Received",
			"Reversed",
			"Cost Recognized",
			"Budget Reserved",
			"Budget Executed",
			"Savings Applied",
			"Investment Applied",
		):
			with self.subTest(effect_type=value):
				self.assertIn(value, effect_type_block)

	def test_the_executive_kpi_row_has_real_tokens_semantic_tone_and_a_hero_metric(self) -> None:
		"""Bloque Home #1 pidió que el KPI dejara de usar `var(--fg-color, #fff)` /
		`var(--border-color, #dfe3e8)` —las variables crudas del marco— y ganara
		jerarquía visual real. La reconstrucción visual definitiva reemplazó por
		completo esa fila de seis métricas (`.nxr-executive-metric`, ahora retirada
		junto con `renderMetrics` — auditoría visual y funcional completa
		post-Dashboard) por la fila real de cinco KPI del mandato
		(`.nxr-kpi-card`/`renderKpiRow`); esta prueba verifica la misma exigencia
		original contra el componente real que la resuelve ahora."""
		code = self._dashboard_code()
		self.assertNotIn("nxr-executive-metric", code)
		self.assertIn('class="nxr-kpi-card nxr-ds-card"', code)
		self.assertIn("data-tone=", code.split("function kpiCardHtml(row) {", 1)[1].split("\n\t}", 1)[0])

		css = (APP_ROOT / "public/css/nexora_executive.css").read_text(encoding="utf-8")
		self.assertNotIn("nxr-executive-metric", css)
		kpi_card_block = css.split(".nxr-kpi-card {", 1)[1].split("\n}", 1)[0]
		# Ya no debe depender de las variables crudas del marco.
		self.assertNotIn("var(--fg-color", kpi_card_block)
		self.assertNotIn("var(--border-color", kpi_card_block)
		# Jerarquía real: la primera tarjeta (Saldo disponible) no compite en
		# igualdad de peso visual con las otras cuatro.
		self.assertIn(".nxr-kpi-row .nxr-kpi-card:first-child {", css)

	def test_bar_row_labels_are_not_starved_of_space_by_the_bar_track(self) -> None:
		"""Bloque Home #3 (Vista operativa). Captura real de "Gastos por categoría"
		mostró la categoría real sembrada por `financial/seeds.py` ("Cuenta Máxima",
		13 caracteres) cortada a "Cuenta Má…" con la tarjeta casi vacía: la fila
		(`minmax(90px, 1fr) minmax(70px, 2fr) auto`) le daba a la barra el doble de
		espacio flexible que a la etiqueta, aunque la etiqueta es el contenido
		legible y la barra solo un apoyo visual. Se invierte esa prioridad y se
		agrega `title` para que el nombre completo siga disponible aunque la
		columna vuelva a quedar angosta con nombres más largos."""
		css = (APP_ROOT / "public/css/nexora_executive.css").read_text(encoding="utf-8")
		bar_row_block = css.split(".nxr-bar-row {", 1)[1].split("\n}", 1)[0]
		self.assertIn("minmax(90px, 2fr)", bar_row_block)
		self.assertNotIn("minmax(70px, 2fr)", bar_row_block)

		code = self._dashboard_code()
		render_bars = code[code.index("function renderBars") : code.index("function renderPayables")]
		self.assertIn('<span title="${escape(rowLabel(row))}">', render_bars)

	def test_quick_link_tiles_use_real_design_system_tokens(self) -> None:
		"""Bloque Home #4 (Acciones rápidas). Mismo defecto que el Bloque Home #1
		(auditoría visual original), aquí en `.nxr-quick-links button` — usado por
		"Tareas frecuentes" y "Accesos recientes" —: `var(--subtle-fg, #f2f5f8)` crudo
		del marco en vez del token real (`--nxr-surface-sunken`) que el sistema de
		diseño ya resuelve para el resto del panel."""
		css = (APP_ROOT / "public/css/nexora_executive.css").read_text(encoding="utf-8")
		quick_links_block = css.split(".nxr-quick-links button {", 1)[1].split("\n}", 1)[0]
		self.assertNotIn("var(--subtle-fg", quick_links_block)
		self.assertIn("var(--nxr-surface-sunken)", quick_links_block)
		self.assertIn("var(--nxr-border)", quick_links_block)
		self.assertIn(".nxr-quick-links button:hover {", css)


if __name__ == "__main__":
	unittest.main()
